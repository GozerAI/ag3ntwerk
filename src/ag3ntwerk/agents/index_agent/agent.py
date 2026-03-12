"""
Index (Index) Agent - Index.

Codename: Index
Core function: Govern data assets, ensure quality, and manage knowledge.

The Index handles all data governance and knowledge management tasks:
- Data governance and stewardship
- Data quality monitoring and enforcement
- Schema management and validation
- Data lineage tracking
- Knowledge management (merged from CKO)
- Data catalog management
- Analytics coordination

Sphere of influence: Data governance, data quality, metadata management,
knowledge management, data lineage, data catalog, analytics enablement.
"""

from typing import Any, Dict, List, Optional
import uuid

from ag3ntwerk.core.base import (
    Manager,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider
from ag3ntwerk.agents.index_agent.managers import (
    DataGovernanceManager,
    AnalyticsManager,
    KnowledgeManager,
)
from ag3ntwerk.agents.index_agent.specialists import (
    DataSteward,
    SchemaAnalyst,
    QualityAnalyst,
    AnalyticsSpecialist,
    KnowledgeCurator,
)
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


# Data governance and knowledge task types
DATA_GOVERNANCE_CAPABILITIES = [
    # Data governance
    "data_governance",
    "data_quality_check",
    "data_profiling",
    "schema_validation",
    "schema_design",
    "data_lineage",
    "data_catalog",
    "data_classification",
    "metadata_management",
    # Knowledge management (from CKO)
    "documentation",
    "knowledge_retrieval",
    "research_synthesis",
    "learning_path",
    "knowledge_base_update",
    "best_practices",
    "faq_generation",
    "glossary_management",
    "tutorial_creation",
    "summary_generation",
    # Analytics
    "data_analysis",
    "analytics_design",
    "metrics_definition",
    "dashboard_design",
]


class Index(Manager):
    """
    Index - Index.

    The Index is responsible for all data governance, data quality,
    and knowledge management within the ag3ntwerk system. It manages
    data assets, ensures quality standards, and maintains the
    organizational knowledge base.

    Codename: Index

    Core Responsibilities:
    - Data governance policy and enforcement
    - Data quality monitoring and improvement
    - Schema management and validation
    - Data lineage tracking and visualization
    - Knowledge base management (from CKO)
    - Data catalog maintenance
    - Analytics enablement

    Example:
        ```python
        cdo = Index(llm_provider=llm)

        task = Task(
            description="Validate customer data against schema",
            task_type="data_quality_check",
            context={"dataset": "customers", "schema": "customer_v2"},
        )
        result = await cdo.execute(task)
        ```
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
    ):
        super().__init__(
            code="Index",
            name="Index",
            domain="Data Governance, Quality, Knowledge Management",
            llm_provider=llm_provider,
        )
        self.codename = "Index"

        self.capabilities = DATA_GOVERNANCE_CAPABILITIES

        # Data governance state
        self._datasets: Dict[str, Dataset] = {}
        self._schemas: Dict[str, Schema] = {}
        self._quality_rules: Dict[str, DataQualityRule] = {}
        self._lineage_edges: Dict[str, LineageEdge] = {}
        self._catalog: Dict[str, DataCatalogEntry] = {}

        # Knowledge management state (from CKO)
        self._knowledge_base: Dict[str, KnowledgeArticle] = {}
        self._documentation_index: Dict[str, str] = {}
        self._learning_paths: Dict[str, List[str]] = {}

        # Initialize and register managers with their specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize and register managers with their specialists."""
        # Create managers
        dgm = DataGovernanceManager(llm_provider=self.llm_provider)
        am = AnalyticsManager(llm_provider=self.llm_provider)
        km = KnowledgeManager(llm_provider=self.llm_provider)

        # Create specialists
        data_steward = DataSteward(llm_provider=self.llm_provider)
        schema_analyst = SchemaAnalyst(llm_provider=self.llm_provider)
        quality_analyst = QualityAnalyst(llm_provider=self.llm_provider)
        analytics_specialist = AnalyticsSpecialist(llm_provider=self.llm_provider)
        knowledge_curator = KnowledgeCurator(llm_provider=self.llm_provider)

        # Register specialists with appropriate managers
        dgm.register_subordinate(data_steward)
        dgm.register_subordinate(schema_analyst)
        dgm.register_subordinate(quality_analyst)
        am.register_subordinate(analytics_specialist)
        km.register_subordinate(knowledge_curator)

        # Register managers with Index
        self.register_subordinate(dgm)
        self.register_subordinate(am)
        self.register_subordinate(km)

    def can_handle(self, task: Task) -> bool:
        """Check if this is a data governance or knowledge task."""
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        """Execute a data governance or knowledge task."""
        task.status = TaskStatus.IN_PROGRESS

        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        return await self._handle_with_llm(task)

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            # Data governance handlers
            "data_governance": self._handle_data_governance,
            "data_quality_check": self._handle_data_quality_check,
            "data_profiling": self._handle_data_profiling,
            "schema_validation": self._handle_schema_validation,
            "schema_design": self._handle_schema_design,
            "data_lineage": self._handle_data_lineage,
            "data_catalog": self._handle_data_catalog,
            "data_classification": self._handle_data_classification,
            "metadata_management": self._handle_metadata_management,
            # Knowledge handlers (from CKO)
            "documentation": self._handle_documentation,
            "knowledge_retrieval": self._handle_knowledge_retrieval,
            "research_synthesis": self._handle_research_synthesis,
            "learning_path": self._handle_learning_path,
            "best_practices": self._handle_best_practices,
            "summary_generation": self._handle_summary_generation,
            # Analytics handlers
            "data_analysis": self._handle_data_analysis,
            "analytics_design": self._handle_analytics_design,
            "metrics_definition": self._handle_metrics_definition,
            # VLS handlers
            "vls_lead_intake": self._handle_vls_lead_intake,
            "vls_knowledge_capture": self._handle_vls_knowledge_capture,
        }
        return handlers.get(task_type)

    # =========================================================================
    # Data Governance Handlers
    # =========================================================================

    async def _handle_data_governance(self, task: Task) -> TaskResult:
        """Handle data governance policy tasks."""
        governance_type = task.context.get("governance_type", "general")

        prompt = f"""As the Index (Index), address this data governance matter.

Governance Type: {governance_type}
Description: {task.description}
Context: {task.context}

Provide governance guidance including:
1. Applicable policies and standards
2. Data ownership and stewardship requirements
3. Access control recommendations
4. Compliance considerations
5. Data lifecycle management
6. Monitoring and enforcement measures"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "governance_type": governance_type,
                "analysis": response,
            },
            metrics={"task_type": "data_governance"},
        )

    async def _handle_data_quality_check(self, task: Task) -> TaskResult:
        """Perform data quality assessment."""
        dataset_id = task.context.get("dataset", "unknown")
        rules = task.context.get("rules", [])

        prompt = f"""As the Index (Index), perform a data quality assessment.

Dataset: {dataset_id}
Description: {task.description}
Quality Rules to Check: {rules if rules else 'Standard quality checks'}
Context: {task.context}

Assess data quality across these dimensions:
1. Completeness - missing values, required fields
2. Accuracy - data correctness and precision
3. Consistency - format and value consistency
4. Timeliness - data freshness and currency
5. Validity - conformance to business rules
6. Uniqueness - duplicate detection

Provide:
- Quality score for each dimension
- Specific issues found
- Recommendations for improvement"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "check_type": "data_quality",
                "dataset": dataset_id,
                "assessment": response,
            },
        )

    async def _handle_data_profiling(self, task: Task) -> TaskResult:
        """Profile a dataset to understand its characteristics."""
        dataset_id = task.context.get("dataset", "unknown")

        prompt = f"""As the Index (Index), profile this dataset.

Dataset: {dataset_id}
Description: {task.description}
Context: {task.context}

Provide a comprehensive data profile including:
1. Dataset overview (rows, columns, size)
2. Column-level statistics
3. Data type distribution
4. Null/missing value analysis
5. Value distribution and patterns
6. Potential data quality issues
7. Relationships and dependencies
8. Recommendations for schema design"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "profile_type": "dataset",
                "dataset": dataset_id,
                "profile": response,
            },
        )

    async def _handle_schema_validation(self, task: Task) -> TaskResult:
        """Validate data against a schema."""
        schema_id = task.context.get("schema", "")
        data = task.context.get("data", {})

        # Check if we have the schema in memory
        if schema_id and schema_id in self._schemas:
            schema = self._schemas[schema_id]
            errors = schema.validate_data(data)
            if errors:
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output={
                        "valid": False,
                        "errors": errors,
                        "schema": schema.name,
                    },
                )
            return TaskResult(
                task_id=task.id,
                success=True,
                output={
                    "valid": True,
                    "schema": schema.name,
                },
            )

        # Use LLM for schema validation guidance
        prompt = f"""As the Index (Index), validate data against schema.

Schema: {schema_id}
Description: {task.description}
Data Sample: {data}
Context: {task.context}

Validate the data and provide:
1. Validation result (pass/fail)
2. Field-by-field validation results
3. Type mismatches found
4. Missing required fields
5. Invalid values
6. Recommendations for fixing issues"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "validation_type": "schema",
                "schema": schema_id,
                "validation": response,
            },
        )

    async def _handle_schema_design(self, task: Task) -> TaskResult:
        """Design a data schema."""
        entity = task.context.get("entity", "")
        requirements = task.context.get("requirements", [])

        prompt = f"""As the Index (Index), design a data schema.

Entity: {entity}
Description: {task.description}
Requirements: {requirements}
Context: {task.context}

Design a comprehensive schema including:
1. Field definitions with types
2. Primary and foreign keys
3. Required vs optional fields
4. Default values
5. Constraints and validations
6. Indexes for performance
7. Relationships to other entities
8. Versioning considerations

Output the schema in a structured format."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "schema",
                "entity": entity,
                "schema_design": response,
            },
        )

    async def _handle_data_lineage(self, task: Task) -> TaskResult:
        """Track or query data lineage."""
        lineage_action = task.context.get("action", "trace")
        dataset_id = task.context.get("dataset", "")

        prompt = f"""As the Index (Index), handle data lineage request.

Action: {lineage_action}
Dataset: {dataset_id}
Description: {task.description}
Context: {task.context}

Provide lineage analysis including:
1. Source systems and datasets
2. Transformation steps
3. Downstream dependencies
4. Data flow visualization
5. Impact analysis for changes
6. Quality propagation assessment"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "lineage_type": lineage_action,
                "dataset": dataset_id,
                "lineage": response,
            },
        )

    async def _handle_data_catalog(self, task: Task) -> TaskResult:
        """Manage the data catalog."""
        catalog_action = task.context.get("action", "search")
        query = task.context.get("query", task.description)

        prompt = f"""As the Index (Index), manage the data catalog.

Action: {catalog_action}
Query: {query}
Description: {task.description}
Context: {task.context}

For the data catalog, provide:
1. Matching catalog entries
2. Dataset descriptions and metadata
3. Access information
4. Related datasets
5. Quality metrics
6. Usage statistics"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "catalog_action": catalog_action,
                "query": query,
                "results": response,
            },
        )

    async def _handle_data_classification(self, task: Task) -> TaskResult:
        """Classify data by sensitivity and type."""
        dataset_id = task.context.get("dataset", "")

        prompt = f"""As the Index (Index), classify this data.

Dataset: {dataset_id}
Description: {task.description}
Context: {task.context}

Classify the data including:
1. Sensitivity level (Public/Internal/Confidential/Secret)
2. PII/PHI detection
3. Regulatory classification (GDPR, HIPAA, etc.)
4. Business criticality
5. Retention requirements
6. Access control recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "classification_type": "data",
                "dataset": dataset_id,
                "classification": response,
            },
        )

    async def _handle_metadata_management(self, task: Task) -> TaskResult:
        """Manage metadata for data assets."""
        asset_id = task.context.get("asset", "")
        metadata_action = task.context.get("action", "describe")

        prompt = f"""As the Index (Index), manage metadata.

Asset: {asset_id}
Action: {metadata_action}
Description: {task.description}
Context: {task.context}

Provide metadata management including:
1. Technical metadata (schema, types, constraints)
2. Business metadata (definitions, owners, usage)
3. Operational metadata (refresh, quality, lineage)
4. Metadata standards compliance
5. Cross-reference with other assets"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "metadata_action": metadata_action,
                "asset": asset_id,
                "metadata": response,
            },
        )

    # =========================================================================
    # Knowledge Management Handlers (from CKO)
    # =========================================================================

    async def _handle_documentation(self, task: Task) -> TaskResult:
        """Create documentation."""
        subject = task.context.get("subject", "")
        doc_format = task.context.get("format", "markdown")
        audience = task.context.get("audience", "developers")

        prompt = f"""As the Index (Index), create documentation.

Subject: {subject}
Format: {doc_format}
Target Audience: {audience}
Description: {task.description}
Context: {task.context}

Create comprehensive documentation including:
1. Overview and purpose
2. Prerequisites and requirements
3. Step-by-step instructions or API reference
4. Examples and use cases
5. Troubleshooting guide
6. Related resources

Format the documentation in {doc_format} with proper structure."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "doc_type": "documentation",
                "format": doc_format,
                "content": response,
            },
        )

    async def _handle_knowledge_retrieval(self, task: Task) -> TaskResult:
        """Retrieve and synthesize knowledge."""
        query = task.description
        sources = task.context.get("sources", [])

        prompt = f"""As the Index (Index), retrieve and synthesize knowledge.

Query: {query}
Sources: {sources if sources else 'All available knowledge'}
Context: {task.context}

Provide a comprehensive answer that:
1. Directly addresses the query
2. Synthesizes information from multiple sources
3. Cites relevant sources and references
4. Identifies gaps in available knowledge
5. Suggests related topics for exploration"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "query": query,
                "synthesis": response,
            },
        )

    async def _handle_research_synthesis(self, task: Task) -> TaskResult:
        """Synthesize research findings."""
        topic = task.context.get("topic", task.description)
        sources = task.context.get("sources", [])

        prompt = f"""As the Index (Index), synthesize research.

Topic: {topic}
Sources: {sources if sources else 'Provide general synthesis'}
Description: {task.description}
Context: {task.context}

Create a research synthesis including:
1. Agent summary
2. Key findings and themes
3. Methodology overview
4. Critical analysis
5. Gaps and limitations
6. Recommendations
7. References"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "synthesis_type": "research",
                "topic": topic,
                "synthesis": response,
            },
        )

    async def _handle_learning_path(self, task: Task) -> TaskResult:
        """Create a learning path."""
        topic = task.context.get("topic", task.description)
        skill_level = task.context.get("skill_level", "beginner")

        prompt = f"""As the Index (Index), create a learning path.

Topic: {topic}
Starting Skill Level: {skill_level}
Description: {task.description}
Context: {task.context}

Create a structured learning path including:
1. Learning objectives
2. Prerequisites
3. Modules with progression
4. Resources for each stage
5. Assessment checkpoints
6. Time estimates
7. Next steps"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "path_type": "learning",
                "topic": topic,
                "skill_level": skill_level,
                "path": response,
            },
        )

    async def _handle_best_practices(self, task: Task) -> TaskResult:
        """Compile best practices."""
        domain = task.context.get("domain", "data management")

        prompt = f"""As the Index (Index), compile best practices.

Domain: {domain}
Description: {task.description}
Context: {task.context}

Compile a best practices guide including:
1. Core principles
2. Do's and don'ts
3. Common pitfalls
4. Examples
5. Implementation checklists
6. Success metrics
7. Further resources"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "doc_type": "best_practices",
                "domain": domain,
                "practices": response,
            },
        )

    async def _handle_summary_generation(self, task: Task) -> TaskResult:
        """Generate a summary."""
        content = task.context.get("content", "")
        summary_type = task.context.get("summary_type", "comprehensive")

        prompt = f"""As the Index (Index), generate a summary.

Summary Type: {summary_type}
Description: {task.description}

Content to summarize:
{content}

Generate a {summary_type} summary that:
1. Captures key points
2. Maintains accuracy
3. Is appropriately concise
4. Highlights conclusions
5. Notes caveats"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "summary_type": summary_type,
                "summary": response,
            },
        )

    # =========================================================================
    # Analytics Handlers
    # =========================================================================

    async def _handle_data_analysis(self, task: Task) -> TaskResult:
        """Perform data analysis."""
        dataset = task.context.get("dataset", "")
        analysis_type = task.context.get("analysis_type", "exploratory")

        prompt = f"""As the Index (Index), perform data analysis.

Dataset: {dataset}
Analysis Type: {analysis_type}
Description: {task.description}
Context: {task.context}

Provide analysis including:
1. Data overview and summary statistics
2. Pattern identification
3. Anomaly detection
4. Trend analysis
5. Correlations and relationships
6. Insights and conclusions
7. Recommended actions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis_type": analysis_type,
                "dataset": dataset,
                "analysis": response,
            },
        )

    async def _handle_analytics_design(self, task: Task) -> TaskResult:
        """Design analytics solutions."""
        objective = task.context.get("objective", "")

        prompt = f"""As the Index (Index), design analytics solution.

Objective: {objective}
Description: {task.description}
Context: {task.context}

Design analytics solution including:
1. Business requirements
2. Data sources needed
3. Metrics and KPIs
4. Analysis methodology
5. Visualization approach
6. Implementation roadmap
7. Maintenance plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "design_type": "analytics",
                "objective": objective,
                "design": response,
            },
        )

    async def _handle_metrics_definition(self, task: Task) -> TaskResult:
        """Define metrics and KPIs."""
        domain = task.context.get("domain", "")

        prompt = f"""As the Index (Index), define metrics.

Domain: {domain}
Description: {task.description}
Context: {task.context}

Define metrics including:
1. Metric name and definition
2. Business purpose
3. Calculation methodology
4. Data sources
5. Refresh frequency
6. Targets and thresholds
7. Ownership and governance"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "definition_type": "metrics",
                "domain": domain,
                "metrics": response,
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

        prompt = f"""As the Index (Index) specializing in data governance
and knowledge management, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide a thorough data-focused response."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=response,
        )

    # =========================================================================
    # Data Management Methods
    # =========================================================================

    def register_dataset(self, dataset: Dataset) -> str:
        """Register a dataset in the catalog."""
        self._datasets[dataset.id] = dataset
        # Also add to catalog
        entry = DataCatalogEntry(
            id=dataset.id,
            name=dataset.name,
            entry_type="dataset",
            description=dataset.description,
            location=dataset.location,
            owner=dataset.owner,
            tags=dataset.tags,
            sensitivity=dataset.sensitivity,
        )
        self._catalog[dataset.id] = entry
        return dataset.id

    def register_schema(self, schema: Schema) -> str:
        """Register a schema."""
        self._schemas[schema.id] = schema
        return schema.id

    def add_quality_rule(self, rule: DataQualityRule) -> str:
        """Add a data quality rule."""
        self._quality_rules[rule.id] = rule
        return rule.id

    def add_lineage(self, edge: LineageEdge) -> str:
        """Add a lineage relationship."""
        self._lineage_edges[edge.id] = edge
        return edge.id

    def add_knowledge_article(self, article: KnowledgeArticle) -> str:
        """Add a knowledge base article."""
        self._knowledge_base[article.id] = article
        return article.id

    async def _handle_vls_lead_intake(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Lead Intake."""
        from ag3ntwerk.modules.vls.stages import execute_lead_intake

        try:
            result = await execute_lead_intake(task.context)

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
                error=f"VLS Lead Intake failed: {e}",
            )

    async def _handle_vls_knowledge_capture(self, task: Task) -> TaskResult:
        """Execute VLS Stage: Knowledge Capture."""
        from ag3ntwerk.modules.vls.stages import execute_knowledge_capture

        try:
            result = await execute_knowledge_capture(task.context)

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
                error=f"VLS Knowledge Capture failed: {e}",
            )

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID."""
        return self._datasets.get(dataset_id)

    def get_schema(self, schema_id: str) -> Optional[Schema]:
        """Get a schema by ID."""
        return self._schemas.get(schema_id)

    def search_catalog(self, query: str) -> List[DataCatalogEntry]:
        """Search the data catalog."""
        results = []
        query_lower = query.lower()
        for entry in self._catalog.values():
            if (
                query_lower in entry.name.lower()
                or query_lower in entry.description.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)
        return results

    def get_lineage(self, dataset_id: str, direction: str = "both") -> List[LineageEdge]:
        """Get lineage for a dataset."""
        results = []
        for edge in self._lineage_edges.values():
            if direction in ("upstream", "both") and edge.target_id == dataset_id:
                results.append(edge)
            if direction in ("downstream", "both") and edge.source_id == dataset_id:
                results.append(edge)
        return results

    def get_governance_status(self) -> Dict[str, Any]:
        """Get current data governance status."""
        return {
            "datasets_registered": len(self._datasets),
            "schemas_registered": len(self._schemas),
            "quality_rules": len(self._quality_rules),
            "lineage_edges": len(self._lineage_edges),
            "catalog_entries": len(self._catalog),
            "knowledge_articles": len(self._knowledge_base),
            "capabilities": self.capabilities,
        }
