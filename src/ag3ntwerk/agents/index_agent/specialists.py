"""
Specialists for the Index (Index) agent.

Specialists are the workers that perform specific operational tasks
within data governance and knowledge management.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.core.base import (
    Specialist,
    Task,
    TaskResult,
    TaskStatus,
)
from ag3ntwerk.llm.base import LLMProvider


class DataSteward(Specialist):
    """
    Specialist responsible for data stewardship.

    Handles data governance policy implementation, data classification,
    and metadata management at the operational level.

    Capabilities:
    - Data governance policy enforcement
    - Data classification and tagging
    - Metadata curation
    - Data ownership management
    - Data issue resolution
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="DS",
            name="Data Steward",
            domain="Data Stewardship, Governance Implementation",
            capabilities=[
                "data_governance",
                "data_classification",
                "metadata_management",
                "data_ownership",
                "data_issue_resolution",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute data stewardship task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "data_governance": self._handle_governance,
            "data_classification": self._handle_classification,
            "metadata_management": self._handle_metadata,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_governance(self, task: Task) -> TaskResult:
        """Handle data governance task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Data Steward, implement data governance for:

Description: {task.description}
Context: {task.context}

Provide:
1. Applicable governance policies
2. Data ownership recommendations
3. Access control requirements
4. Compliance considerations
5. Implementation steps"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"governance_plan": response, "specialist": self.code},
        )

    async def _handle_classification(self, task: Task) -> TaskResult:
        """Handle data classification task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Data Steward, classify this data:

Description: {task.description}
Context: {task.context}

Determine:
1. Sensitivity level (Public/Internal/Confidential/Secret)
2. PII/PHI indicators
3. Regulatory classification (GDPR, HIPAA, etc.)
4. Retention requirements
5. Access recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"classification": response, "specialist": self.code},
        )

    async def _handle_metadata(self, task: Task) -> TaskResult:
        """Handle metadata management task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Data Steward, manage metadata for:

Description: {task.description}
Context: {task.context}

Provide:
1. Technical metadata (schema, types, formats)
2. Business metadata (definitions, owners, usage)
3. Operational metadata (refresh, quality, lineage)
4. Metadata quality assessment
5. Enrichment recommendations"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"metadata": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic stewardship task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Data Steward, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide data stewardship guidance and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class SchemaAnalyst(Specialist):
    """
    Specialist responsible for schema analysis and design.

    Handles schema validation, design, and data lineage tracking.

    Capabilities:
    - Schema validation
    - Schema design
    - Data lineage analysis
    - Data modeling
    - Schema evolution management
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="SA",
            name="Schema Analyst",
            domain="Schema Design, Data Modeling, Lineage",
            capabilities=[
                "schema_validation",
                "schema_design",
                "data_lineage",
                "data_modeling",
                "schema_evolution",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute schema analysis task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "schema_validation": self._handle_validation,
            "schema_design": self._handle_design,
            "data_lineage": self._handle_lineage,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_validation(self, task: Task) -> TaskResult:
        """Handle schema validation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Schema Analyst, validate this schema:

Description: {task.description}
Context: {task.context}

Analyze:
1. Field definitions and types
2. Required vs optional fields
3. Constraints and validations
4. Normalization assessment
5. Performance considerations
6. Recommendations for improvement"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"validation": response, "specialist": self.code},
        )

    async def _handle_design(self, task: Task) -> TaskResult:
        """Handle schema design task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Schema Analyst, design a schema for:

Description: {task.description}
Context: {task.context}

Design including:
1. Entity definition and purpose
2. Field specifications with types
3. Primary and foreign keys
4. Indexes for query optimization
5. Constraints and validations
6. Relationships to other entities
7. Versioning strategy"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"schema_design": response, "specialist": self.code},
        )

    async def _handle_lineage(self, task: Task) -> TaskResult:
        """Handle data lineage task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Schema Analyst, trace data lineage for:

Description: {task.description}
Context: {task.context}

Provide lineage analysis:
1. Source systems and datasets
2. Transformation steps
3. Data flow diagram
4. Downstream dependencies
5. Impact of changes
6. Quality propagation"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"lineage": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic schema task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Schema Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide schema analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class QualityAnalyst(Specialist):
    """
    Specialist responsible for data quality analysis.

    Handles data quality checks, profiling, and quality rule management.

    Capabilities:
    - Data quality checks
    - Data profiling
    - Quality rule definition
    - Quality monitoring
    - Issue identification and tracking
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="QA",
            name="Quality Analyst",
            domain="Data Quality, Profiling, Monitoring",
            capabilities=[
                "data_quality_check",
                "data_profiling",
                "quality_rule_definition",
                "quality_monitoring",
                "quality_issue_tracking",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute data quality task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "data_quality_check": self._handle_quality_check,
            "data_profiling": self._handle_profiling,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_quality_check(self, task: Task) -> TaskResult:
        """Handle data quality check task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Quality Analyst, assess data quality:

Description: {task.description}
Context: {task.context}

Evaluate across dimensions:
1. Completeness - missing values, required fields
2. Accuracy - data correctness
3. Consistency - format and value consistency
4. Timeliness - data freshness
5. Validity - business rule conformance
6. Uniqueness - duplicate detection

Provide quality scores and specific issues."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"quality_assessment": response, "specialist": self.code},
        )

    async def _handle_profiling(self, task: Task) -> TaskResult:
        """Handle data profiling task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Quality Analyst, profile this dataset:

Description: {task.description}
Context: {task.context}

Provide profiling results:
1. Dataset overview (rows, columns, size)
2. Column-level statistics
3. Data type distribution
4. Null/missing value analysis
5. Value patterns and distributions
6. Potential data quality issues
7. Anomaly detection"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"profile": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic quality task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Quality Analyst, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide data quality analysis and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class AnalyticsSpecialist(Specialist):
    """
    Specialist responsible for analytics and reporting.

    Handles data analysis, metrics definition, dashboard design,
    and analytics solution architecture.

    Capabilities:
    - Data analysis
    - Analytics design
    - Metrics definition
    - Dashboard design
    - Reporting
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="AS",
            name="Analytics Specialist",
            domain="Analytics, Metrics, Reporting, Dashboards",
            capabilities=[
                "data_analysis",
                "analytics_design",
                "metrics_definition",
                "dashboard_design",
                "reporting",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute analytics task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "data_analysis": self._handle_analysis,
            "analytics_design": self._handle_design,
            "metrics_definition": self._handle_metrics,
            "dashboard_design": self._handle_dashboard,
            "reporting": self._handle_reporting,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_analysis(self, task: Task) -> TaskResult:
        """Handle data analysis task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        dataset = task.context.get("dataset", "")
        analysis_type = task.context.get("analysis_type", "exploratory")

        prompt = f"""As an Analytics Specialist, perform data analysis:

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
6. Statistical significance
7. Insights and conclusions
8. Recommended actions"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analysis": response,
                "analysis_type": analysis_type,
                "specialist": self.code,
            },
        )

    async def _handle_design(self, task: Task) -> TaskResult:
        """Handle analytics design task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        objective = task.context.get("objective", task.description)

        prompt = f"""As an Analytics Specialist, design analytics solution:

Objective: {objective}
Description: {task.description}
Context: {task.context}

Design solution including:
1. Business requirements analysis
2. Data sources identification
3. Metrics and KPIs definition
4. Analysis methodology
5. Data pipeline architecture
6. Visualization approach
7. Implementation roadmap
8. Maintenance and monitoring plan"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "analytics_design": response,
                "objective": objective,
                "specialist": self.code,
            },
        )

    async def _handle_metrics(self, task: Task) -> TaskResult:
        """Handle metrics definition task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        domain = task.context.get("domain", "")

        prompt = f"""As an Analytics Specialist, define metrics:

Domain: {domain}
Description: {task.description}
Context: {task.context}

Define metrics including:
1. Metric name and definition
2. Business purpose and value
3. Calculation methodology
4. Data sources required
5. Refresh frequency
6. Targets and thresholds
7. Visualization recommendations
8. Ownership and governance"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "metrics_definition": response,
                "domain": domain,
                "specialist": self.code,
            },
        )

    async def _handle_dashboard(self, task: Task) -> TaskResult:
        """Handle dashboard design task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        audience = task.context.get("audience", "business users")

        prompt = f"""As an Analytics Specialist, design dashboard:

Audience: {audience}
Description: {task.description}
Context: {task.context}

Design dashboard including:
1. Dashboard purpose and objectives
2. Key metrics and KPIs to display
3. Layout and organization
4. Chart types and visualizations
5. Interactivity and drill-downs
6. Data refresh requirements
7. Access control recommendations
8. Implementation guidelines"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "dashboard_design": response,
                "audience": audience,
                "specialist": self.code,
            },
        )

    async def _handle_reporting(self, task: Task) -> TaskResult:
        """Handle reporting task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        report_type = task.context.get("report_type", "standard")
        audience = task.context.get("audience", "management")

        prompt = f"""As an Analytics Specialist, create report:

Report Type: {report_type}
Audience: {audience}
Description: {task.description}
Context: {task.context}

Create report including:
1. Agent summary
2. Key metrics and highlights
3. Trend analysis
4. Comparative analysis
5. Insights and findings
6. Visualizations
7. Recommendations
8. Appendix with detailed data"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "report": response,
                "report_type": report_type,
                "audience": audience,
                "specialist": self.code,
            },
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic analytics task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As an Analytics Specialist, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide analytics guidance and recommendations."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )


class KnowledgeCurator(Specialist):
    """
    Specialist responsible for knowledge curation.

    Handles documentation, knowledge base management, and content creation.

    Capabilities:
    - Documentation creation
    - Knowledge retrieval
    - Content curation
    - Learning material creation
    - Best practices documentation
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        super().__init__(
            code="KC",
            name="Knowledge Curator",
            domain="Knowledge Curation, Documentation, Content",
            capabilities=[
                "documentation",
                "knowledge_retrieval",
                "research_synthesis",
                "learning_path",
                "best_practices",
                "tutorial_creation",
                "summary_generation",
            ],
            llm_provider=llm_provider,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute knowledge curation task."""
        task.status = TaskStatus.IN_PROGRESS

        handlers = {
            "documentation": self._handle_documentation,
            "knowledge_retrieval": self._handle_retrieval,
            "learning_path": self._handle_learning_path,
            "best_practices": self._handle_best_practices,
        }

        handler = handlers.get(task.task_type, self._handle_generic)
        return await handler(task)

    async def _handle_documentation(self, task: Task) -> TaskResult:
        """Handle documentation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        doc_format = task.context.get("format", "markdown")
        audience = task.context.get("audience", "technical")

        prompt = f"""As a Knowledge Curator, create documentation:

Description: {task.description}
Format: {doc_format}
Audience: {audience}
Context: {task.context}

Create comprehensive documentation including:
1. Overview and purpose
2. Prerequisites
3. Step-by-step instructions
4. Examples and code samples
5. Troubleshooting guide
6. References and resources"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={
                "documentation": response,
                "format": doc_format,
                "specialist": self.code,
            },
        )

    async def _handle_retrieval(self, task: Task) -> TaskResult:
        """Handle knowledge retrieval task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Knowledge Curator, retrieve and synthesize knowledge:

Query: {task.description}
Context: {task.context}

Provide:
1. Direct answer to the query
2. Supporting information
3. Related topics
4. Sources and references
5. Gaps in available knowledge"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"knowledge": response, "specialist": self.code},
        )

    async def _handle_learning_path(self, task: Task) -> TaskResult:
        """Handle learning path creation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        skill_level = task.context.get("skill_level", "beginner")

        prompt = f"""As a Knowledge Curator, create a learning path:

Topic: {task.description}
Skill Level: {skill_level}
Context: {task.context}

Design a learning path with:
1. Learning objectives
2. Prerequisites
3. Progressive modules
4. Resources for each stage
5. Hands-on exercises
6. Assessment checkpoints
7. Time estimates"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"learning_path": response, "specialist": self.code},
        )

    async def _handle_best_practices(self, task: Task) -> TaskResult:
        """Handle best practices documentation task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Knowledge Curator, compile best practices:

Topic: {task.description}
Context: {task.context}

Compile best practices including:
1. Core principles
2. Recommended approaches
3. Common pitfalls to avoid
4. Real-world examples
5. Implementation checklists
6. Success metrics"""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"best_practices": response, "specialist": self.code},
        )

    async def _handle_generic(self, task: Task) -> TaskResult:
        """Handle generic knowledge task."""
        if not self.llm_provider:
            return TaskResult(task_id=task.id, success=False, error="No LLM provider")

        prompt = f"""As a Knowledge Curator, handle this task:

Task Type: {task.task_type}
Description: {task.description}
Context: {task.context}

Provide knowledge curation output."""

        response = await self.reason(prompt, task.context)

        return TaskResult(
            task_id=task.id,
            success=True,
            output={"response": response, "specialist": self.code},
        )
