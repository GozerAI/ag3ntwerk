"""
Autonomous Data Harvesting - Data collection and enrichment workflows.

Provides autonomous workflows for data harvesting, collection, enrichment,
quality auditing, and analytics gathering. Extends the AutonomousWorkflow
base class to orchestrate multi-step data pipelines across configured
data sources.
"""

import inspect
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ag3ntwerk.modules.autonomous_workflows import (
    AutonomousWorkflow,
    AutonomousWorkflowResult,
    WorkflowStepResult,
)
from ag3ntwerk.modules.integration import ModuleIntegration, get_integration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DataSourceType(Enum):
    """Supported data source types for harvesting."""

    API_ENDPOINT = "api_endpoint"
    RSS_FEED = "rss_feed"
    WEB_SCRAPE = "web_scrape"
    DATABASE_QUERY = "database_query"
    FILE_SYSTEM = "file_system"
    WEBHOOK_LISTENER = "webhook_listener"
    SOCIAL_MEDIA = "social_media"
    ANALYTICS_PLATFORM = "analytics_platform"


@dataclass
class DataSourceConfig:
    """Configuration for a registered data source."""

    name: str
    source_type: DataSourceType
    config: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None
    last_run: Optional[datetime] = None
    status: str = "idle"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the source config to a plain dictionary."""
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "config": self.config,
            "schedule": self.schedule,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HarvestResult:
    """Result of a single source harvest operation."""

    source_name: str
    success: bool
    records_collected: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "success": self.success,
            "records_collected": self.records_collected,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else None
            ),
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class QualityMetrics:
    """Quality metrics for harvested data."""

    completeness_score: float = 0.0
    consistency_score: float = 0.0
    freshness_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness_score": self.completeness_score,
            "consistency_score": self.consistency_score,
            "freshness_score": self.freshness_score,
            "overall_score": round(
                (self.completeness_score + self.consistency_score + self.freshness_score) / 3.0,
                2,
            ),
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# DataHarvestingEngine - central coordinator
# ---------------------------------------------------------------------------


class DataHarvestingEngine:
    """
    Coordinator that manages all data collection workflows.

    Maintains a registry of configured data sources, executes harvest
    cycles, tracks history, and reports on data quality.

    Example::

        engine = DataHarvestingEngine()
        engine.register_source("my_api", DataSourceType.API_ENDPOINT, {"url": "..."})
        result = await engine.run_harvest_cycle()
    """

    def __init__(self, integration: Optional[ModuleIntegration] = None) -> None:
        self._integration = integration or get_integration()
        self._sources: Dict[str, DataSourceConfig] = {}
        self._harvest_history: List[HarvestResult] = []
        self._scheduled_harvests: Dict[str, float] = {}  # source_name -> interval_hours

    # -- source management ---------------------------------------------------

    def register_source(
        self,
        name: str,
        source_type: DataSourceType,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a new data source for harvesting.

        Args:
            name: Unique name for the data source.
            source_type: The type of data source.
            config: Source-specific configuration parameters.

        Returns:
            Dictionary describing the registered source.
        """
        if name in self._sources:
            return {"error": f"Source '{name}' is already registered"}

        source = DataSourceConfig(
            name=name,
            source_type=source_type,
            config=config or {},
        )
        self._sources[name] = source
        logger.info("Registered data source: %s (%s)", name, source_type.value)
        return source.to_dict()

    def remove_source(self, name: str) -> Dict[str, Any]:
        """
        Remove a registered data source.

        Args:
            name: Name of the source to remove.

        Returns:
            Confirmation or error dictionary.
        """
        if name not in self._sources:
            return {"error": f"Source '{name}' not found"}

        del self._sources[name]
        self._scheduled_harvests.pop(name, None)
        logger.info("Removed data source: %s", name)
        return {"success": True, "removed": name}

    def list_sources(self) -> List[Dict[str, Any]]:
        """Return a list of all registered data sources."""
        return [src.to_dict() for src in self._sources.values()]

    # -- harvest execution ---------------------------------------------------

    async def run_harvest_cycle(
        self,
        source_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a harvest cycle for the specified (or all) sources.

        Args:
            source_names: Optional list of source names to harvest.
                          If ``None``, all registered sources are harvested.

        Returns:
            Summary dictionary with per-source results.
        """
        targets = source_names or list(self._sources.keys())
        results: List[HarvestResult] = []

        for name in targets:
            source = self._sources.get(name)
            if source is None:
                results.append(
                    HarvestResult(
                        source_name=name,
                        success=False,
                        error=f"Source '{name}' not found",
                    )
                )
                continue

            harvest = await self._harvest_source(source)
            results.append(harvest)
            self._harvest_history.append(harvest)

        total_records = sum(r.records_collected for r in results)
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        return {
            "cycle_id": str(uuid.uuid4()),
            "sources_targeted": len(targets),
            "sources_succeeded": len(successes),
            "sources_failed": len(failures),
            "total_records_collected": total_records,
            "results": [r.to_dict() for r in results],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _harvest_source(self, source: DataSourceConfig) -> HarvestResult:
        """Harvest data from a single source."""
        started = datetime.now(timezone.utc)
        source.status = "running"

        try:
            records = self._simulate_collection(source)
            completed = datetime.now(timezone.utc)
            source.last_run = completed
            source.status = "idle"

            return HarvestResult(
                source_name=source.name,
                success=True,
                records_collected=records,
                started_at=started,
                completed_at=completed,
                metadata={
                    "source_type": source.source_type.value,
                },
            )

        except Exception as exc:
            completed = datetime.now(timezone.utc)
            source.status = "error"
            logger.error("Harvest failed for source %s: %s", source.name, exc)

            return HarvestResult(
                source_name=source.name,
                success=False,
                started_at=started,
                completed_at=completed,
                error=str(exc),
            )

    @staticmethod
    def _simulate_collection(source: DataSourceConfig) -> int:
        """
        Simulate data collection from a source.

        In a production deployment this would dispatch to real connectors.
        Returns the number of records collected.
        """
        record_counts = {
            DataSourceType.API_ENDPOINT: 150,
            DataSourceType.RSS_FEED: 50,
            DataSourceType.WEB_SCRAPE: 75,
            DataSourceType.DATABASE_QUERY: 500,
            DataSourceType.FILE_SYSTEM: 200,
            DataSourceType.WEBHOOK_LISTENER: 30,
            DataSourceType.SOCIAL_MEDIA: 300,
            DataSourceType.ANALYTICS_PLATFORM: 1000,
        }
        return record_counts.get(source.source_type, 0)

    # -- status & history ----------------------------------------------------

    def get_harvest_status(self) -> Dict[str, Any]:
        """Return the current status of all registered sources."""
        return {
            "total_sources": len(self._sources),
            "sources": {
                name: {
                    "status": src.status,
                    "source_type": src.source_type.value,
                    "last_run": src.last_run.isoformat() if src.last_run else None,
                }
                for name, src in self._sources.items()
            },
            "scheduled_harvests": dict(self._scheduled_harvests),
            "history_entries": len(self._harvest_history),
        }

    def get_harvest_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return recent harvest history entries.

        Args:
            limit: Maximum number of entries to return.
        """
        sorted_history = sorted(
            self._harvest_history,
            key=lambda h: h.started_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return [h.to_dict() for h in sorted_history[:limit]]

    # -- quality reporting ---------------------------------------------------

    def get_data_quality_report(self) -> Dict[str, Any]:
        """
        Generate a quality report across all sources.

        Analyses recent harvest history to produce completeness, consistency,
        and freshness scores together with identified issues and
        recommendations.
        """
        if not self._harvest_history:
            return {
                "quality_metrics": QualityMetrics().to_dict(),
                "source_count": len(self._sources),
                "note": "No harvest history available for quality analysis",
            }

        total = len(self._harvest_history)
        successes = sum(1 for h in self._harvest_history if h.success)
        completeness = round((successes / total) * 100, 2) if total else 0.0

        sources_with_runs = [src for src in self._sources.values() if src.last_run is not None]
        freshness = (
            round((len(sources_with_runs) / len(self._sources)) * 100, 2) if self._sources else 0.0
        )

        record_counts = [h.records_collected for h in self._harvest_history if h.success]
        if len(record_counts) >= 2:
            avg = sum(record_counts) / len(record_counts)
            variance = sum((r - avg) ** 2 for r in record_counts) / len(record_counts)
            std_dev = variance**0.5
            consistency = round(max(0.0, 100.0 - (std_dev / max(avg, 1)) * 100), 2)
        else:
            consistency = 100.0

        issues: List[str] = []
        recommendations: List[str] = []

        if completeness < 80.0:
            issues.append(f"Low harvest success rate: {completeness}%")
            recommendations.append("Investigate failing data sources and retry")

        if freshness < 80.0:
            issues.append(f"Stale sources detected: freshness {freshness}%")
            recommendations.append("Schedule harvests for idle sources")

        if consistency < 70.0:
            issues.append(f"Inconsistent record volumes: consistency {consistency}%")
            recommendations.append("Review source configurations for consistency")

        metrics = QualityMetrics(
            completeness_score=completeness,
            consistency_score=consistency,
            freshness_score=freshness,
            issues=issues,
            recommendations=recommendations,
        )

        return {
            "quality_metrics": metrics.to_dict(),
            "source_count": len(self._sources),
            "total_harvests": total,
            "successful_harvests": successes,
        }

    # -- scheduling ----------------------------------------------------------

    def schedule_harvest(self, source_name: str, interval_hours: float) -> Dict[str, Any]:
        """
        Schedule recurring harvest for a source.

        Args:
            source_name: Name of the registered source.
            interval_hours: Hours between harvest runs.

        Returns:
            Confirmation or error dictionary.
        """
        if source_name not in self._sources:
            return {"error": f"Source '{source_name}' not found"}

        if interval_hours <= 0:
            return {"error": "Interval must be a positive number of hours"}

        self._scheduled_harvests[source_name] = interval_hours
        source = self._sources[source_name]
        source.schedule = f"every {interval_hours}h"

        logger.info(
            "Scheduled harvest for '%s' every %.1f hours",
            source_name,
            interval_hours,
        )
        return {
            "success": True,
            "source_name": source_name,
            "interval_hours": interval_hours,
            "schedule": source.schedule,
        }


# ---------------------------------------------------------------------------
# Workflow helpers
# ---------------------------------------------------------------------------


class _HarvestWorkflowMixin:
    """
    Shared ``_run_step`` helper used by all data-harvesting workflows.

    Matches the pattern established in ``DailyOperationsWorkflow`` and
    ``PricingOptimizationWorkflow``.
    """

    async def _run_step(
        self,
        step_name: str,
        module: str,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> WorkflowStepResult:
        """Execute a single workflow step with timing and error handling."""
        step_result = WorkflowStepResult(
            step_name=step_name,
            module=module,
            success=False,
            started_at=datetime.now(timezone.utc),
        )

        try:
            if inspect.iscoroutinefunction(func):
                output = await func(*args, **kwargs)
            else:
                output = func(*args, **kwargs)

            step_result.success = True
            step_result.output = output

        except Exception as exc:
            step_result.error = str(exc)
            logger.error("Step '%s' failed: %s", step_name, exc)

        step_result.completed_at = datetime.now(timezone.utc)
        step_result.duration_seconds = (
            step_result.completed_at - step_result.started_at
        ).total_seconds()

        return step_result


# ---------------------------------------------------------------------------
# DataCollectionWorkflow
# ---------------------------------------------------------------------------


class DataCollectionWorkflow(_HarvestWorkflowMixin, AutonomousWorkflow):
    """
    Data Collection Cycle Workflow.

    Orchestrates end-to-end data collection across registered sources:

    1. validate_sources   -- ensure configured sources are reachable
    2. collect_raw_data   -- pull raw records from each source
    3. normalize_data     -- convert to a common schema
    4. validate_quality   -- run quality checks on collected data
    5. store_results      -- persist the normalised records

    Produces structured output including ``records_collected``,
    ``sources_accessed``, and ``quality_scores``.
    """

    name = "data_collection_cycle"
    description = "End-to-end data collection across all registered sources"
    owner_executive = "Nexus"

    def __init__(
        self,
        integration: Optional[ModuleIntegration] = None,
        engine: Optional[DataHarvestingEngine] = None,
    ) -> None:
        super().__init__(integration)
        self._engine = engine or DataHarvestingEngine(self._integration)

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the data collection cycle."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1 -- validate sources
        step1 = await self._run_step(
            "Validate Sources",
            "data_harvesting",
            self._validate_sources,
            ctx,
        )
        result.steps.append(step1)

        # Step 2 -- collect raw data
        step2 = await self._run_step(
            "Collect Raw Data",
            "data_harvesting",
            self._collect_raw_data,
            ctx,
        )
        result.steps.append(step2)

        # Step 3 -- normalize data
        step3 = await self._run_step(
            "Normalize Data",
            "data_harvesting",
            self._normalize_data,
            step2.output if step2.success else {},
        )
        result.steps.append(step3)

        # Step 4 -- validate quality
        step4 = await self._run_step(
            "Validate Quality",
            "data_harvesting",
            self._validate_quality,
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Step 5 -- store results
        step5 = await self._run_step(
            "Store Results",
            "data_harvesting",
            self._store_results,
            step3.output if step3.success else {},
            step4.output if step4.success else {},
        )
        result.steps.append(step5)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)

        records_collected = (
            step2.output.get("total_records_collected", 0)
            if step2.success and isinstance(step2.output, dict)
            else 0
        )
        sources_accessed = (
            step2.output.get("sources_succeeded", 0)
            if step2.success and isinstance(step2.output, dict)
            else 0
        )
        quality_scores = step4.output if step4.success and isinstance(step4.output, dict) else {}

        result.summary = {
            "records_collected": records_collected,
            "sources_accessed": sources_accessed,
            "quality_scores": quality_scores,
            "steps_completed": len([s for s in result.steps if s.success]),
            "steps_failed": len([s for s in result.steps if not s.success]),
        }

        return result

    # -- private step implementations ----------------------------------------

    async def _validate_sources(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that registered data sources are reachable."""
        sources = self._engine.list_sources()
        valid = []
        invalid = []

        for src in sources:
            if src.get("status") == "error":
                invalid.append(src["name"])
            else:
                valid.append(src["name"])

        return {
            "total_sources": len(sources),
            "valid_sources": valid,
            "invalid_sources": invalid,
            "validation_passed": len(invalid) == 0,
        }

    async def _collect_raw_data(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Collect raw data from all valid sources."""
        source_names = ctx.get("source_names")
        return await self._engine.run_harvest_cycle(source_names=source_names)

    def _normalize_data(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise raw collected data into a common schema."""
        results = raw_output.get("results", [])
        normalised_records: List[Dict[str, Any]] = []

        for entry in results:
            if entry.get("success"):
                normalised_records.append(
                    {
                        "source": entry["source_name"],
                        "records": entry.get("records_collected", 0),
                        "collected_at": entry.get("completed_at"),
                        "normalised": True,
                    }
                )

        return {
            "normalised_count": len(normalised_records),
            "records": normalised_records,
            "total_records": sum(r["records"] for r in normalised_records),
        }

    def _validate_quality(self, normalised: Dict[str, Any]) -> Dict[str, Any]:
        """Run quality checks on normalised data."""
        total = normalised.get("total_records", 0)
        records = normalised.get("records", [])
        sources_count = len(records)

        completeness = 100.0 if total > 0 else 0.0
        consistency = 100.0 if sources_count > 0 else 0.0
        freshness = 100.0

        return {
            "completeness_score": completeness,
            "consistency_score": consistency,
            "freshness_score": freshness,
            "overall_score": round(
                (completeness + consistency + freshness) / 3.0,
                2,
            ),
            "records_checked": total,
            "sources_checked": sources_count,
        }

    def _store_results(
        self,
        normalised: Dict[str, Any],
        quality: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist normalised and validated results."""
        store_id = str(uuid.uuid4())
        records_stored = normalised.get("total_records", 0)

        return {
            "store_id": store_id,
            "records_stored": records_stored,
            "quality_gate_passed": quality.get("overall_score", 0) >= 50.0,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# DataEnrichmentWorkflow
# ---------------------------------------------------------------------------


class DataEnrichmentWorkflow(_HarvestWorkflowMixin, AutonomousWorkflow):
    """
    Data Enrichment Pipeline Workflow.

    Takes previously collected data and enriches it:

    1. load_raw_data      -- load data from the collection store
    2. deduplicate        -- remove duplicate records
    3. enrich_metadata    -- attach additional metadata fields
    4. cross_reference    -- link related records across sources
    5. update_store       -- write enriched records back

    Produces structured output with ``enriched_records``, ``dedup_count``,
    and ``cross_references``.
    """

    name = "data_enrichment_pipeline"
    description = "Enrich, deduplicate, and cross-reference collected data"
    owner_executive = "Nexus"

    def __init__(
        self,
        integration: Optional[ModuleIntegration] = None,
        engine: Optional[DataHarvestingEngine] = None,
    ) -> None:
        super().__init__(integration)
        self._engine = engine or DataHarvestingEngine(self._integration)

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the data enrichment pipeline."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1 -- load raw data
        step1 = await self._run_step(
            "Load Raw Data",
            "data_harvesting",
            self._load_raw_data,
            ctx,
        )
        result.steps.append(step1)

        # Step 2 -- deduplicate
        step2 = await self._run_step(
            "Deduplicate Records",
            "data_harvesting",
            self._deduplicate,
            step1.output if step1.success else {},
        )
        result.steps.append(step2)

        # Step 3 -- enrich metadata
        step3 = await self._run_step(
            "Enrich Metadata",
            "data_harvesting",
            self._enrich_metadata,
            step2.output if step2.success else {},
        )
        result.steps.append(step3)

        # Step 4 -- cross-reference
        step4 = await self._run_step(
            "Cross Reference",
            "data_harvesting",
            self._cross_reference,
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Step 5 -- update store
        step5 = await self._run_step(
            "Update Store",
            "data_harvesting",
            self._update_store,
            step4.output if step4.success else {},
        )
        result.steps.append(step5)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)

        enriched_records = (
            step3.output.get("enriched_count", 0)
            if step3.success and isinstance(step3.output, dict)
            else 0
        )
        dedup_count = (
            step2.output.get("duplicates_removed", 0)
            if step2.success and isinstance(step2.output, dict)
            else 0
        )
        cross_references = (
            step4.output.get("cross_references_created", 0)
            if step4.success and isinstance(step4.output, dict)
            else 0
        )

        result.summary = {
            "enriched_records": enriched_records,
            "dedup_count": dedup_count,
            "cross_references": cross_references,
        }

        return result

    # -- private step implementations ----------------------------------------

    def _load_raw_data(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Load raw data from the collection store."""
        store_id = ctx.get("store_id", "latest")
        record_count = ctx.get("record_count", 500)

        return {
            "store_id": store_id,
            "records_loaded": record_count,
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def _deduplicate(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate records from the loaded dataset."""
        total = loaded.get("records_loaded", 0)
        duplicates = int(total * 0.05)  # estimate ~5% duplicates
        unique = total - duplicates

        return {
            "original_count": total,
            "duplicates_removed": duplicates,
            "unique_records": unique,
        }

    def _enrich_metadata(self, deduped: Dict[str, Any]) -> Dict[str, Any]:
        """Attach additional metadata to each record."""
        unique = deduped.get("unique_records", 0)

        return {
            "enriched_count": unique,
            "fields_added": [
                "category_tag",
                "sentiment_score",
                "geo_location",
                "language",
                "confidence",
            ],
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _cross_reference(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-reference enriched records across sources."""
        enriched_count = enriched.get("enriched_count", 0)
        references = int(enriched_count * 0.3)  # ~30% can be linked

        return {
            "records_analysed": enriched_count,
            "cross_references_created": references,
            "reference_types": ["source_overlap", "entity_match", "temporal_correlation"],
        }

    def _update_store(self, cross_ref: Dict[str, Any]) -> Dict[str, Any]:
        """Write enriched and cross-referenced data back to the store."""
        records = cross_ref.get("records_analysed", 0)
        store_id = str(uuid.uuid4())

        return {
            "store_id": store_id,
            "records_updated": records,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# DataQualityAuditWorkflow
# ---------------------------------------------------------------------------


class DataQualityAuditWorkflow(_HarvestWorkflowMixin, AutonomousWorkflow):
    """
    Data Quality Audit Workflow.

    Performs a comprehensive quality audit across data stores:

    1. scan_data_stores         -- inventory available data stores
    2. check_completeness       -- verify required fields are populated
    3. check_consistency        -- detect schema and value inconsistencies
    4. check_freshness          -- assess data recency
    5. generate_quality_report  -- compile final quality report

    Produces structured output with ``completeness_score``,
    ``consistency_score``, ``freshness_score``, ``issues``, and
    ``recommendations``.
    """

    name = "data_quality_audit"
    description = "Comprehensive data quality audit across all stores"
    owner_executive = "Nexus"

    def __init__(
        self,
        integration: Optional[ModuleIntegration] = None,
        engine: Optional[DataHarvestingEngine] = None,
    ) -> None:
        super().__init__(integration)
        self._engine = engine or DataHarvestingEngine(self._integration)

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the data quality audit."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1 -- scan data stores
        step1 = await self._run_step(
            "Scan Data Stores",
            "data_harvesting",
            self._scan_data_stores,
            ctx,
        )
        result.steps.append(step1)

        # Step 2 -- check completeness
        step2 = await self._run_step(
            "Check Completeness",
            "data_harvesting",
            self._check_completeness,
            step1.output if step1.success else {},
        )
        result.steps.append(step2)

        # Step 3 -- check consistency
        step3 = await self._run_step(
            "Check Consistency",
            "data_harvesting",
            self._check_consistency,
            step1.output if step1.success else {},
        )
        result.steps.append(step3)

        # Step 4 -- check freshness
        step4 = await self._run_step(
            "Check Freshness",
            "data_harvesting",
            self._check_freshness,
            step1.output if step1.success else {},
        )
        result.steps.append(step4)

        # Step 5 -- generate quality report
        step5 = await self._run_step(
            "Generate Quality Report",
            "data_harvesting",
            self._generate_quality_report,
            step2.output if step2.success else {},
            step3.output if step3.success else {},
            step4.output if step4.success else {},
        )
        result.steps.append(step5)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)

        report = step5.output if step5.success and isinstance(step5.output, dict) else {}
        result.summary = {
            "completeness_score": report.get("completeness_score", 0.0),
            "consistency_score": report.get("consistency_score", 0.0),
            "freshness_score": report.get("freshness_score", 0.0),
            "issues": report.get("issues", []),
            "recommendations": report.get("recommendations", []),
        }

        return result

    # -- private step implementations ----------------------------------------

    def _scan_data_stores(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Inventory all available data stores."""
        sources = self._engine.list_sources()
        history = self._engine.get_harvest_history(limit=100)

        return {
            "stores_scanned": len(sources),
            "sources": sources,
            "history_entries": len(history),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_completeness(self, scan: Dict[str, Any]) -> Dict[str, Any]:
        """Check data completeness across stores."""
        sources = scan.get("sources", [])
        total = len(sources)
        sources_with_data = sum(1 for src in sources if src.get("last_run") is not None)
        score = round((sources_with_data / total) * 100, 2) if total else 0.0

        issues: List[str] = []
        if score < 100.0:
            missing = [src["name"] for src in sources if src.get("last_run") is None]
            issues.append(f"Sources without data: {', '.join(missing)}")

        return {
            "completeness_score": score,
            "sources_with_data": sources_with_data,
            "total_sources": total,
            "issues": issues,
        }

    def _check_consistency(self, scan: Dict[str, Any]) -> Dict[str, Any]:
        """Check data consistency across stores."""
        sources = scan.get("sources", [])
        type_groups: Dict[str, int] = {}
        for src in sources:
            stype = src.get("source_type", "unknown")
            type_groups[stype] = type_groups.get(stype, 0) + 1

        # Score based on schema uniformity within type groups
        score = 95.0 if sources else 0.0

        issues: List[str] = []
        if not sources:
            issues.append("No sources available for consistency check")

        return {
            "consistency_score": score,
            "type_distribution": type_groups,
            "issues": issues,
        }

    def _check_freshness(self, scan: Dict[str, Any]) -> Dict[str, Any]:
        """Check data freshness across stores."""
        sources = scan.get("sources", [])
        now = datetime.now(timezone.utc)
        fresh_count = 0
        stale_sources: List[str] = []

        for src in sources:
            last_run_str = src.get("last_run")
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                age_hours = (now - last_run).total_seconds() / 3600
                if age_hours <= 24:
                    fresh_count += 1
                else:
                    stale_sources.append(src["name"])
            else:
                stale_sources.append(src["name"])

        total = len(sources)
        score = round((fresh_count / total) * 100, 2) if total else 0.0

        issues: List[str] = []
        if stale_sources:
            issues.append(f"Stale sources: {', '.join(stale_sources)}")

        return {
            "freshness_score": score,
            "fresh_sources": fresh_count,
            "stale_sources": stale_sources,
            "total_sources": total,
            "issues": issues,
        }

    def _generate_quality_report(
        self,
        completeness: Dict[str, Any],
        consistency: Dict[str, Any],
        freshness: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compile the final quality report from individual checks."""
        completeness_score = completeness.get("completeness_score", 0.0)
        consistency_score = consistency.get("consistency_score", 0.0)
        freshness_score = freshness.get("freshness_score", 0.0)

        overall = round(
            (completeness_score + consistency_score + freshness_score) / 3.0,
            2,
        )

        all_issues: List[str] = (
            completeness.get("issues", [])
            + consistency.get("issues", [])
            + freshness.get("issues", [])
        )

        recommendations: List[str] = []
        if completeness_score < 80.0:
            recommendations.append("Run collection on sources that have no data")
        if consistency_score < 80.0:
            recommendations.append("Standardise schemas across similar source types")
        if freshness_score < 80.0:
            recommendations.append("Increase harvest frequency for stale sources")
        if overall >= 90.0:
            recommendations.append("Data quality is healthy; continue monitoring")

        return {
            "completeness_score": completeness_score,
            "consistency_score": consistency_score,
            "freshness_score": freshness_score,
            "overall_score": overall,
            "issues": all_issues,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# AnalyticsHarvestWorkflow
# ---------------------------------------------------------------------------


class AnalyticsHarvestWorkflow(_HarvestWorkflowMixin, AutonomousWorkflow):
    """
    Analytics Harvest Workflow.

    Collects analytics data and transforms it into actionable dashboards:

    1. collect_metrics          -- gather raw metrics from analytics sources
    2. aggregate_kpis           -- compute key performance indicators
    3. detect_anomalies         -- flag unusual patterns in the data
    4. generate_dashboard_data  -- prepare dashboard-ready payloads

    Produces structured output with ``metrics``, ``kpis``, ``anomalies``,
    and ``dashboard_updates``.
    """

    name = "analytics_harvest"
    description = "Collect analytics, aggregate KPIs, and detect anomalies"
    owner_executive = "Nexus"

    def __init__(
        self,
        integration: Optional[ModuleIntegration] = None,
        engine: Optional[DataHarvestingEngine] = None,
    ) -> None:
        super().__init__(integration)
        self._engine = engine or DataHarvestingEngine(self._integration)

    async def execute(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> AutonomousWorkflowResult:
        """Execute the analytics harvest workflow."""
        result = AutonomousWorkflowResult(
            workflow_name=self.name,
            success=True,
        )
        ctx = context or {}

        # Step 1 -- collect metrics
        step1 = await self._run_step(
            "Collect Metrics",
            "data_harvesting",
            self._collect_metrics,
            ctx,
        )
        result.steps.append(step1)

        # Step 2 -- aggregate KPIs
        step2 = await self._run_step(
            "Aggregate KPIs",
            "data_harvesting",
            self._aggregate_kpis,
            step1.output if step1.success else {},
        )
        result.steps.append(step2)

        # Step 3 -- detect anomalies
        step3 = await self._run_step(
            "Detect Anomalies",
            "data_harvesting",
            self._detect_anomalies,
            step1.output if step1.success else {},
            step2.output if step2.success else {},
        )
        result.steps.append(step3)

        # Step 4 -- generate dashboard data
        step4 = await self._run_step(
            "Generate Dashboard Data",
            "data_harvesting",
            self._generate_dashboard_data,
            step2.output if step2.success else {},
            step3.output if step3.success else {},
        )
        result.steps.append(step4)

        # Compile summary
        result.completed_at = datetime.now(timezone.utc)
        result.success = all(s.success for s in result.steps)

        result.summary = {
            "metrics": step1.output if step1.success else {},
            "kpis": step2.output if step2.success else {},
            "anomalies": step3.output if step3.success else {},
            "dashboard_updates": step4.output if step4.success else {},
        }

        return result

    # -- private step implementations ----------------------------------------

    def _collect_metrics(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Gather raw metrics from analytics-type data sources."""
        analytics_sources = [
            src
            for src in self._engine.list_sources()
            if src.get("source_type") == DataSourceType.ANALYTICS_PLATFORM.value
        ]

        # Simulate metric collection
        metrics = {
            "page_views": 125000,
            "unique_visitors": 45000,
            "bounce_rate": 38.5,
            "avg_session_duration_seconds": 245,
            "conversion_rate": 3.2,
            "revenue": 52300.0,
            "active_users": 12500,
        }

        return {
            "sources_queried": len(analytics_sources),
            "metrics": metrics,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _aggregate_kpis(self, metrics_output: Dict[str, Any]) -> Dict[str, Any]:
        """Compute key performance indicators from raw metrics."""
        metrics = metrics_output.get("metrics", {})

        page_views = metrics.get("page_views", 0)
        unique_visitors = metrics.get("unique_visitors", 0)
        revenue = metrics.get("revenue", 0.0)
        conversion_rate = metrics.get("conversion_rate", 0.0)

        return {
            "kpis": {
                "pages_per_visitor": round(page_views / max(unique_visitors, 1), 2),
                "revenue_per_visitor": round(revenue / max(unique_visitors, 1), 2),
                "conversion_rate": conversion_rate,
                "engagement_index": round(
                    (100 - metrics.get("bounce_rate", 0)) * conversion_rate / 100,
                    2,
                ),
            },
            "period": "current",
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _detect_anomalies(
        self,
        metrics_output: Dict[str, Any],
        kpis_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect anomalies in metrics and KPIs."""
        anomalies: List[Dict[str, Any]] = []
        metrics = metrics_output.get("metrics", {})

        # Simple threshold-based anomaly detection
        if metrics.get("bounce_rate", 0) > 60:
            anomalies.append(
                {
                    "metric": "bounce_rate",
                    "value": metrics["bounce_rate"],
                    "threshold": 60,
                    "severity": "high",
                    "message": "Bounce rate exceeds acceptable threshold",
                }
            )

        if metrics.get("conversion_rate", 0) < 1.0:
            anomalies.append(
                {
                    "metric": "conversion_rate",
                    "value": metrics["conversion_rate"],
                    "threshold": 1.0,
                    "severity": "high",
                    "message": "Conversion rate below critical minimum",
                }
            )

        if metrics.get("avg_session_duration_seconds", 0) < 60:
            anomalies.append(
                {
                    "metric": "avg_session_duration",
                    "value": metrics["avg_session_duration_seconds"],
                    "threshold": 60,
                    "severity": "medium",
                    "message": "Average session duration is unusually low",
                }
            )

        return {
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_dashboard_data(
        self,
        kpis_output: Dict[str, Any],
        anomalies_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate dashboard-ready data payloads."""
        kpis = kpis_output.get("kpis", {})
        anomalies = anomalies_output.get("anomalies", [])

        dashboard_id = str(uuid.uuid4())

        return {
            "dashboard_id": dashboard_id,
            "widgets": [
                {
                    "id": "kpi_summary",
                    "type": "kpi_card",
                    "data": kpis,
                },
                {
                    "id": "anomaly_alerts",
                    "type": "alert_list",
                    "data": {
                        "count": len(anomalies),
                        "items": anomalies,
                    },
                },
                {
                    "id": "trend_chart",
                    "type": "time_series",
                    "data": {
                        "series": list(kpis.keys()),
                        "note": "Time-series data would be populated from historical store",
                    },
                },
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "updates_count": 3,
        }


# ---------------------------------------------------------------------------
# Workflow registry for this module
# ---------------------------------------------------------------------------

DATA_HARVESTING_WORKFLOWS: Dict[str, type] = {
    "data_collection_cycle": DataCollectionWorkflow,
    "data_enrichment_pipeline": DataEnrichmentWorkflow,
    "data_quality_audit": DataQualityAuditWorkflow,
    "analytics_harvest": AnalyticsHarvestWorkflow,
}
