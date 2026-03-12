"""
Workflow Library Plugin - Connects ag3ntwerk to the Harvester workflow database.

Provides search, recommendation, and statistics for automation workflows
across multiple tools (n8n, Zapier, Make, LangChain, CrewAI, AutoGen, IFTTT).

The plugin connects to the Harvester's PostgreSQL database (shared DB approach)
and provides async read-only access to the workflow library.
"""

import json
import os
import logging
from typing import Any, Dict, List, Optional

import httpx

from ag3ntwerk.core.plugins.base import Plugin
from ag3ntwerk.core.plugins._utils import hook

logger = logging.getLogger(__name__)

# Default connection string — overridden via plugin config
DEFAULT_DSN = os.environ.get("WORKFLOW_DB_DSN", "postgresql://localhost:5435/workflow_library")
DEFAULT_OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


class WorkflowLibraryPlugin(Plugin):
    """
    Search, recommend, and manage automation workflows from the library.

    Connects to the Harvester's PostgreSQL database to provide the ag3ntwerk
    with access to thousands of classified and scored automation workflows.
    """

    name = "workflow-library"
    version = "1.0.0"
    description = "Search, recommend, and manage automation workflows from the library"
    author = "ag3ntwerk"

    def __init__(self):
        super().__init__()
        self._pool = None
        self._ollama_url = DEFAULT_OLLAMA_URL
        self._http_client: Optional[httpx.AsyncClient] = None

    async def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate plugin configuration."""
        errors = []
        # database_url is optional — has a default
        return errors

    async def on_startup(self) -> None:
        """Connect to the Harvester's PostgreSQL database."""
        try:
            import asyncpg
        except ImportError:
            logger.error(
                "asyncpg is required for workflow-library plugin. "
                "Install with: pip install asyncpg"
            )
            raise

        dsn = self._config.get("database_url", DEFAULT_DSN)
        self._ollama_url = self._config.get("ollama_url", DEFAULT_OLLAMA_URL)
        self._http_client = httpx.AsyncClient(timeout=30.0)
        try:
            self._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=5,
                command_timeout=10,
            )
            # Verify connection
            async with self._pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM workflows")
                logger.info(f"Workflow Library connected: {count} workflows available")
        except Exception as e:
            logger.error(f"Failed to connect to workflow library DB: {e}")
            self._pool = None
            raise

    async def on_shutdown(self) -> None:
        """Close database connection pool and HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Workflow Library disconnected")

    # ─── Core Methods ─────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        min_score: int = 0,
        limit: int = 20,
        semantic: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across the workflow library.

        Args:
            query: Search query string
            tool_type: Filter by tool (n8n, zapier, make, langchain, crewai, autogen, etc.)
            category: Filter by category (lead-gen-crm, ai-agent, orchestration, etc.)
            min_score: Minimum quality score (0-100)
            limit: Maximum results to return
            semantic: If True, also include vector similarity matches

        Returns:
            List of workflow summaries ranked by relevance
        """
        if not self._pool:
            return []

        # Build dynamic WHERE clause
        params: list = [query]
        param_idx = 2

        # Text search condition
        text_condition = "search_vector @@ plainto_tsquery('english', $1)"

        # If semantic, also match by vector similarity
        query_embedding = None
        if semantic:
            query_embedding = await self._get_embedding(query)

        filter_conditions = []
        if tool_type:
            filter_conditions.append(f"tool_type = ${param_idx}")
            params.append(tool_type)
            param_idx += 1

        if category:
            filter_conditions.append(f"primary_category = ${param_idx}")
            params.append(category)
            param_idx += 1

        if min_score > 0:
            filter_conditions.append(f"quality_score >= ${param_idx}")
            params.append(min_score)
            param_idx += 1

        cap = min(limit, 50)

        if query_embedding is not None:
            # Hybrid: text OR vector match
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
            vector_param_idx = param_idx
            params.append(embedding_str)
            param_idx += 1
            params.append(cap)

            match_condition = (
                f"({text_condition} OR "
                f"(embedding IS NOT NULL AND 1 - (embedding <=> ${vector_param_idx}::vector) > 0.3))"
            )
            filters_sql = (" AND " + " AND ".join(filter_conditions)) if filter_conditions else ""

            sql = f"""
                SELECT id, workflow_name, original_description, source, tool_type,
                       primary_category, tags, quality_score, node_types,
                       estimated_complexity, trigger_type, language,
                       ts_rank(search_vector, plainto_tsquery('english', $1)) AS text_rank,
                       CASE WHEN embedding IS NOT NULL
                            THEN 1 - (embedding <=> ${vector_param_idx}::vector)
                            ELSE 0 END AS vector_sim
                FROM workflows
                WHERE {match_condition}{filters_sql}
                ORDER BY (ts_rank(search_vector, plainto_tsquery('english', $1)) * 0.5
                          + CASE WHEN embedding IS NOT NULL
                                 THEN 1 - (embedding <=> ${vector_param_idx}::vector)
                                 ELSE 0 END * 0.5) DESC,
                         quality_score DESC
                LIMIT ${param_idx}
            """
        else:
            # Text-only search (original behavior)
            conditions = [text_condition] + filter_conditions
            params.append(cap)
            where = " AND ".join(conditions)

            sql = f"""
                SELECT id, workflow_name, original_description, source, tool_type,
                       primary_category, tags, quality_score, node_types,
                       estimated_complexity, trigger_type, language,
                       ts_rank(search_vector, plainto_tsquery('english', $1)) AS rank
                FROM workflows
                WHERE {where}
                ORDER BY rank DESC, quality_score DESC
                LIMIT ${param_idx}
            """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [self._row_to_summary(row) for row in rows]

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single workflow by ID with full details.

        Args:
            workflow_id: UUID of the workflow

        Returns:
            Full workflow data including JSON, or None if not found
        """
        if not self._pool:
            return None

        sql = """
            SELECT id, hash, workflow_name, original_description, source, source_url,
                   tool_type, language, workflow_json, tool_metadata,
                   primary_category, secondary_categories, tags,
                   quality_score, node_types, node_count, trigger_type,
                   estimated_complexity, credentials_required,
                   has_code_node, has_description, has_documentation,
                   author_username, author_profile_url,
                   discovered_at, updated_at
            FROM workflows
            WHERE id = $1
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, workflow_id)

        if not row:
            return None

        result = dict(row)
        # Convert special types
        if result.get("workflow_json"):
            result["workflow_json"] = (
                json.loads(result["workflow_json"])
                if isinstance(result["workflow_json"], str)
                else result["workflow_json"]
            )
        if result.get("tool_metadata"):
            result["tool_metadata"] = (
                json.loads(result["tool_metadata"])
                if isinstance(result["tool_metadata"], str)
                else result["tool_metadata"]
            )
        if result.get("discovered_at"):
            result["discovered_at"] = str(result["discovered_at"])
        if result.get("updated_at"):
            result["updated_at"] = str(result["updated_at"])

        return result

    async def recommend(
        self,
        task_description: str,
        tool_type: Optional[str] = None,
        agent_code: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Recommend workflows using hybrid ranking: text + vector + quality + learning.

        Combines four signals:
          - text_rank (0.35): PostgreSQL full-text search relevance
          - vector_sim (0.35): Cosine similarity via pgvector embeddings
          - quality (0.20): Normalized quality_score
          - learning_boost (0.10): Historical success/failure from learning system

        Args:
            task_description: Natural language description of the task
            tool_type: Optional tool type filter
            agent_code: Optional agent code for learning personalization
            limit: Number of recommendations

        Returns:
            List of recommended workflow summaries with ranking scores
        """
        if not self._pool:
            return []

        # Generate query embedding for vector similarity
        query_embedding = await self._get_embedding(task_description)

        filter_conditions = ["quality_score > 0"]
        params: list = [task_description]
        param_idx = 2

        if tool_type:
            filter_conditions.append(f"tool_type = ${param_idx}")
            params.append(tool_type)
            param_idx += 1

        # Fetch more candidates than needed so we can re-rank with learning boost
        fetch_limit = min(limit * 4, 80)

        if query_embedding is not None:
            # Hybrid text + vector matching
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
            vector_param_idx = param_idx
            params.append(embedding_str)
            param_idx += 1
            params.append(fetch_limit)

            match_condition = (
                "(search_vector @@ plainto_tsquery('english', $1) OR "
                f"(embedding IS NOT NULL AND 1 - (embedding <=> ${vector_param_idx}::vector) > 0.3))"
            )
            filters_sql = " AND ".join(filter_conditions)

            sql = f"""
                SELECT id, workflow_name, original_description, source, tool_type,
                       primary_category, tags, quality_score, node_types,
                       estimated_complexity, trigger_type, language,
                       ts_rank(search_vector, plainto_tsquery('english', $1)) AS text_rank,
                       CASE WHEN embedding IS NOT NULL
                            THEN 1 - (embedding <=> ${vector_param_idx}::vector)
                            ELSE 0 END AS vector_sim
                FROM workflows
                WHERE {match_condition} AND {filters_sql}
                ORDER BY (ts_rank(search_vector, plainto_tsquery('english', $1)) * 0.5
                          + CASE WHEN embedding IS NOT NULL
                                 THEN 1 - (embedding <=> ${vector_param_idx}::vector)
                                 ELSE 0 END * 0.5) DESC
                LIMIT ${param_idx}
            """
        else:
            # Fallback: text-only matching
            params.append(fetch_limit)
            filters_sql = " AND ".join(filter_conditions)

            sql = f"""
                SELECT id, workflow_name, original_description, source, tool_type,
                       primary_category, tags, quality_score, node_types,
                       estimated_complexity, trigger_type, language,
                       ts_rank(search_vector, plainto_tsquery('english', $1)) AS text_rank,
                       0::float AS vector_sim
                FROM workflows
                WHERE search_vector @@ plainto_tsquery('english', $1) AND {filters_sql}
                ORDER BY text_rank DESC
                LIMIT ${param_idx}
            """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        # Re-rank with learning boost
        candidates = []
        for row in rows:
            summary = self._row_to_summary(row)
            text_rank = float(row.get("text_rank", 0))
            vector_sim = float(row.get("vector_sim", 0))
            quality_norm = float(row.get("quality_score", 0)) / 100.0
            learning_boost = await self._get_learning_boost(str(row["id"]))

            # Hybrid score: text_rank * 0.35 + vector_sim * 0.35 + quality * 0.20 + learning * 0.10
            combined = (
                text_rank * 0.35 + vector_sim * 0.35 + quality_norm * 0.20 + learning_boost * 0.10
            )
            summary["_combined_score"] = round(combined, 4)
            summary["_text_rank"] = round(text_rank, 4)
            summary["_vector_sim"] = round(vector_sim, 4)
            summary["_learning_boost"] = round(learning_boost, 4)
            candidates.append(summary)

        # Sort by combined score descending
        candidates.sort(key=lambda x: x["_combined_score"], reverse=True)

        return candidates[: min(limit, 20)]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics about the workflow library.

        Returns:
            Dictionary with counts by tool_type, category, source, etc.
        """
        if not self._pool:
            return {"error": "Not connected to workflow library"}

        async with self._pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM workflows")

            by_tool = await conn.fetch(
                "SELECT tool_type, COUNT(*) as count FROM workflows GROUP BY tool_type ORDER BY count DESC"
            )
            by_category = await conn.fetch(
                "SELECT primary_category, COUNT(*) as count FROM workflows "
                "WHERE primary_category IS NOT NULL GROUP BY primary_category ORDER BY count DESC"
            )
            by_source = await conn.fetch(
                "SELECT source, COUNT(*) as count FROM workflows GROUP BY source ORDER BY count DESC"
            )
            quality_dist = await conn.fetch(
                """SELECT
                    CASE
                        WHEN quality_score >= 80 THEN 'excellent'
                        WHEN quality_score >= 60 THEN 'good'
                        WHEN quality_score >= 40 THEN 'fair'
                        ELSE 'low'
                    END as quality_tier,
                    COUNT(*) as count
                FROM workflows
                GROUP BY quality_tier
                ORDER BY count DESC"""
            )

        return {
            "total_workflows": total,
            "by_tool_type": [dict(r) for r in by_tool],
            "by_category": [dict(r) for r in by_category],
            "by_source": [dict(r) for r in by_source],
            "quality_distribution": [dict(r) for r in quality_dist],
        }

    # ─── Deploy & Execute Methods ─────────────────────────────────────────

    def _get_n8n_integration(self):
        """Lazy-load the n8n WorkflowIntegration."""
        if not hasattr(self, "_n8n") or self._n8n is None:
            from ag3ntwerk.integrations.business.workflows import (
                WorkflowIntegration,
                WorkflowProvider,
            )

            self._n8n = WorkflowIntegration(
                provider=WorkflowProvider.N8N,
                n8n_url=self._config.get("n8n_url", "http://localhost:5678"),
                n8n_api_key=self._config.get("n8n_api_key", ""),
            )
        return self._n8n

    async def deploy_workflow(
        self,
        workflow_id: str,
        activate: bool = False,
        deployed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deploy an n8n workflow from the library to a running n8n instance.

        Fetches the workflow JSON from the library, pushes it to n8n via API,
        and records the deployment in the tracking table.

        Args:
            workflow_id: UUID of the workflow in the library
            activate: Whether to activate the workflow immediately
            deployed_by: Agent code or user identifier

        Returns:
            Deployment details including n8n workflow ID
        """
        if not self._pool:
            raise RuntimeError("Not connected to workflow library")

        # Fetch the workflow
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        tool_type = workflow.get("tool_type", "n8n")
        if tool_type != "n8n":
            raise ValueError(
                f"Only n8n workflows can be deployed to n8n. "
                f"This workflow is tool_type='{tool_type}'"
            )

        wf_json = workflow.get("workflow_json", {})
        if not wf_json or not isinstance(wf_json, dict):
            raise ValueError("Workflow has no valid JSON definition")

        # Push to n8n
        n8n = self._get_n8n_integration()
        result = await n8n.create_workflow(
            name=workflow.get("workflow_name", "Library Workflow"),
            nodes=wf_json.get("nodes", []),
            connections=wf_json.get("connections", {}),
            settings=wf_json.get("settings"),
            active=activate,
        )

        n8n_workflow_id = str(result.get("id", ""))

        # Record deployment
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO workflow_deployments
                   (workflow_id, n8n_workflow_id, deployed_by, activated)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (workflow_id, n8n_workflow_id) DO UPDATE
                   SET deployed_at = NOW(), activated = $4""",
                workflow_id,
                n8n_workflow_id,
                deployed_by,
                activate,
            )

        logger.info(
            f"Deployed workflow {workflow_id} → n8n:{n8n_workflow_id} "
            f"(active={activate}, by={deployed_by})"
        )

        return {
            "library_workflow_id": workflow_id,
            "n8n_workflow_id": n8n_workflow_id,
            "name": workflow.get("workflow_name"),
            "activated": activate,
            "deployed_by": deployed_by,
        }

    async def execute_deployed(
        self,
        n8n_workflow_id: str,
        data: Optional[Dict[str, Any]] = None,
        library_workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a deployed workflow on n8n and track the outcome.

        Args:
            n8n_workflow_id: The n8n workflow ID
            data: Input data for the execution
            library_workflow_id: Optional library UUID for tracking

        Returns:
            Execution result
        """
        n8n = self._get_n8n_integration()
        run = await n8n.execute_workflow(n8n_workflow_id, data)

        # Update deployment stats
        if self._pool and library_workflow_id:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE workflow_deployments
                           SET execution_count = execution_count + 1,
                               last_executed_at = NOW(),
                               last_status = $1
                           WHERE n8n_workflow_id = $2""",
                        run.status,
                        n8n_workflow_id,
                    )
            except Exception as e:
                logger.warning(f"Failed to update deployment stats: {e}")

        # Fire learning hook
        try:
            from ag3ntwerk.core.plugins import get_plugin_manager

            manager = get_plugin_manager()
            await manager.fire_hook(
                "workflow.executed",
                {
                    "workflow_id": library_workflow_id or n8n_workflow_id,
                    "success": run.status == "success",
                    "tool_type": "n8n",
                    "agent_code": "Nexus",
                    "task_type": "workflow_execution",
                    "error": run.error if run.error else None,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to fire workflow.executed hook: {e}")

        return {
            "execution_id": run.id,
            "n8n_workflow_id": n8n_workflow_id,
            "library_workflow_id": library_workflow_id,
            "status": run.status,
            "data": run.data,
        }

    async def list_deployments(
        self,
        workflow_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List workflow deployments.

        Args:
            workflow_id: Optional filter by library workflow UUID

        Returns:
            List of deployment records
        """
        if not self._pool:
            return []

        if workflow_id:
            sql = """
                SELECT d.*, w.workflow_name
                FROM workflow_deployments d
                JOIN workflows w ON w.id = d.workflow_id
                WHERE d.workflow_id = $1
                ORDER BY d.deployed_at DESC
            """
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, workflow_id)
        else:
            sql = """
                SELECT d.*, w.workflow_name
                FROM workflow_deployments d
                JOIN workflows w ON w.id = d.workflow_id
                ORDER BY d.deployed_at DESC
                LIMIT 50
            """
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql)

        return [
            {
                "id": str(r["id"]),
                "workflow_id": str(r["workflow_id"]),
                "workflow_name": r["workflow_name"],
                "n8n_workflow_id": r["n8n_workflow_id"],
                "deployed_by": r["deployed_by"],
                "deployed_at": str(r["deployed_at"]) if r["deployed_at"] else None,
                "activated": r["activated"],
                "execution_count": r["execution_count"],
                "last_executed_at": str(r["last_executed_at"]) if r["last_executed_at"] else None,
                "last_status": r["last_status"],
            }
            for r in rows
        ]

    async def list_executions(
        self,
        n8n_workflow_id: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List recent executions for a deployed workflow.

        Args:
            n8n_workflow_id: The n8n workflow ID
            status: Optional status filter
            limit: Maximum results

        Returns:
            List of execution summaries
        """
        n8n = self._get_n8n_integration()
        runs = await n8n.list_executions(
            workflow_id=n8n_workflow_id,
            status=status,
            limit=limit,
        )

        return [
            {
                "execution_id": r.id,
                "workflow_id": r.workflow_id,
                "status": r.status,
                "started_at": str(r.started_at) if r.started_at else None,
                "finished_at": str(r.finished_at) if r.finished_at else None,
            }
            for r in runs
        ]

    # ─── Similarity Search ──────────────────────────────────────────────

    async def find_similar(
        self,
        workflow_id: str,
        limit: int = 10,
        min_similarity: float = 0.3,
        tool_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find workflows similar to a given workflow by embedding distance.

        Uses the pgvector HNSW index for efficient nearest-neighbor lookup.

        Args:
            workflow_id: UUID of the reference workflow
            limit: Maximum results (default 10)
            min_similarity: Minimum cosine similarity threshold (0-1)
            tool_type: Optional filter to only show similar workflows of a specific tool

        Returns:
            List of workflow summaries with similarity scores
        """
        if not self._pool:
            return []

        params: list = [workflow_id, min_similarity]
        param_idx = 3

        filter_sql = ""
        if tool_type:
            filter_sql = f" AND w2.tool_type = ${param_idx}"
            params.append(tool_type)
            param_idx += 1

        params.append(min(limit, 50))

        sql = f"""
            SELECT w2.id, w2.workflow_name, w2.original_description, w2.source,
                   w2.tool_type, w2.primary_category, w2.tags, w2.quality_score,
                   w2.node_types, w2.estimated_complexity, w2.trigger_type, w2.language,
                   1 - (w2.embedding <=> w1.embedding) AS similarity
            FROM workflows w1
            JOIN workflows w2 ON w1.id != w2.id
            WHERE w1.id = $1
              AND w1.embedding IS NOT NULL
              AND w2.embedding IS NOT NULL
              AND 1 - (w2.embedding <=> w1.embedding) > $2
              {filter_sql}
            ORDER BY w2.embedding <=> w1.embedding
            LIMIT ${param_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        results = []
        for row in rows:
            summary = self._row_to_summary(row)
            summary["similarity"] = round(float(row["similarity"]), 4)
            results.append(summary)

        return results

    async def find_similar_by_text(
        self,
        text: str,
        limit: int = 10,
        min_similarity: float = 0.3,
        tool_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find workflows similar to a text description by embedding distance.

        Embeds the input text via Ollama and finds nearest neighbors.

        Args:
            text: Description text to find similar workflows for
            limit: Maximum results (default 10)
            min_similarity: Minimum cosine similarity threshold (0-1)
            tool_type: Optional filter by tool type

        Returns:
            List of workflow summaries with similarity scores
        """
        if not self._pool:
            return []

        query_embedding = await self._get_embedding(text)
        if query_embedding is None:
            return []

        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        params: list = [embedding_str, min_similarity]
        param_idx = 3

        filter_sql = ""
        if tool_type:
            filter_sql = f" AND tool_type = ${param_idx}"
            params.append(tool_type)
            param_idx += 1

        params.append(min(limit, 50))

        sql = f"""
            SELECT id, workflow_name, original_description, source,
                   tool_type, primary_category, tags, quality_score,
                   node_types, estimated_complexity, trigger_type, language,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM workflows
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> $1::vector) > $2
              {filter_sql}
            ORDER BY embedding <=> $1::vector
            LIMIT ${param_idx}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        results = []
        for row in rows:
            summary = self._row_to_summary(row)
            summary["similarity"] = round(float(row["similarity"]), 4)
            results.append(summary)

        return results

    # ─── Embedding & Learning Helpers ─────────────────────────────────────

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding vector via Ollama's /api/embeddings endpoint.

        Mirrors OllamaEmbeddingProvider.embed_text() from
        ag3ntwerk/integrations/vector/base.py, but uses the plugin's httpx client.

        Args:
            text: Text to embed

        Returns:
            768-dimensional float vector, or None on failure
        """
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.post(
                f"{self._ollama_url}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text[:4000]},
            )
            if resp.status_code != 200:
                logger.warning(f"Ollama embedding failed: {resp.status_code}")
                return None

            data = resp.json()
            embedding = data.get("embedding")
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                return embedding
            return None

        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    async def _get_learning_boost(self, workflow_id: str) -> float:
        """
        Get a learning-based boost for a workflow based on historical outcomes.

        Queries the learning system for past execution outcomes of this workflow.
        Returns a normalized score in [0, 1]:
          - 1.0 = all executions succeeded
          - 0.5 = no history (neutral)
          - 0.0 = all executions failed

        Args:
            workflow_id: The workflow UUID

        Returns:
            Float in [0, 1], default 0.5 (neutral)
        """
        try:
            from ag3ntwerk.learning.orchestrator import get_learning_orchestrator

            orchestrator = get_learning_orchestrator()

            # Query recent outcomes for this workflow
            outcomes = await orchestrator.get_recent_outcomes(
                task_type="workflow_execution",
                context_filter={"workflow_id": workflow_id},
                limit=20,
            )

            if not outcomes:
                return 0.5  # No history — neutral

            successes = sum(1 for o in outcomes if o.get("success"))
            total = len(outcomes)
            # Normalize: successes/total gives [0, 1]
            return successes / total

        except (ImportError, AttributeError):
            # Learning system not available or missing method
            return 0.5
        except Exception as e:
            logger.debug(f"Learning boost lookup failed: {e}")
            return 0.5

    # ─── Event Hooks ──────────────────────────────────────────────────────

    @hook("task.planning", priority=40)
    async def suggest_workflows(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """When agents plan tasks, suggest relevant workflows."""
        task_desc = event.get("task_description", "")
        if not task_desc or not self._pool:
            return None

        try:
            recommendations = await self.recommend(task_desc, limit=3)
            if recommendations:
                return {"suggested_workflows": recommendations}
        except Exception as e:
            logger.warning(f"Failed to suggest workflows: {e}")

        return None

    @hook("workflow.executed", priority=50)
    async def record_workflow_outcome(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Record workflow execution outcomes for learning.

        When a workflow from the library is executed (by any agent),
        record the result so the learning system can improve future
        recommendations — e.g., prefer workflows that succeed more often,
        down-rank workflows that frequently fail.

        Expected event keys:
            workflow_id: str — the workflow library UUID
            success: bool — whether execution succeeded
            effectiveness: float (0-1) — optional quality rating
            agent_code: str — which agent ran it
            task_type: str — the originating task type
            error: str — optional error message if failed
        """
        workflow_id = event.get("workflow_id")
        if not workflow_id:
            return None

        try:
            from ag3ntwerk.learning.orchestrator import get_learning_orchestrator
            from ag3ntwerk.learning.models import HierarchyPath

            orchestrator = get_learning_orchestrator()

            hierarchy_path = HierarchyPath(
                agent=event.get("agent_code", "Nexus"),
                manager="workflow-library",
                specialist=None,
            )

            record_id = await orchestrator.record_outcome(
                task_id=workflow_id,
                task_type=event.get("task_type", "workflow_execution"),
                hierarchy_path=hierarchy_path,
                success=event.get("success", True),
                effectiveness=event.get("effectiveness"),
                error=event.get("error"),
                output_summary=f"Workflow {workflow_id} execution",
                context={
                    "source": "workflow-library",
                    "workflow_id": workflow_id,
                    "agent_code": event.get("agent_code"),
                    "tool_type": event.get("tool_type"),
                },
            )

            logger.debug(f"Recorded workflow outcome: {record_id}")
            return {"learning_record_id": record_id}

        except ImportError:
            logger.debug("Learning system not available, skipping outcome recording")
        except Exception as e:
            logger.warning(f"Failed to record workflow outcome: {e}")

        return None

    @hook("workflow.selected", priority=50)
    async def record_workflow_selection(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Track which workflows are selected from recommendations.

        This helps the learning system understand user preferences
        and improve future recommendation ranking.

        Expected event keys:
            workflow_id: str — the selected workflow UUID
            task_description: str — what the user was trying to do
            recommendation_position: int — where it appeared in the list
            total_recommendations: int — how many were offered
        """
        workflow_id = event.get("workflow_id")
        if not workflow_id:
            return None

        try:
            from ag3ntwerk.learning.orchestrator import get_learning_orchestrator
            from ag3ntwerk.learning.models import HierarchyPath

            orchestrator = get_learning_orchestrator()

            hierarchy_path = HierarchyPath(
                agent="Nexus",
                manager="workflow-library",
                specialist="recommendations",
            )

            record_id = await orchestrator.record_outcome(
                task_id=f"selection-{workflow_id}",
                task_type="workflow_selection",
                hierarchy_path=hierarchy_path,
                success=True,
                effectiveness=1.0
                - (
                    event.get("recommendation_position", 0)
                    / max(event.get("total_recommendations", 1), 1)
                ),
                output_summary=f"Selected workflow {workflow_id} for: {event.get('task_description', 'N/A')[:100]}",
                context={
                    "source": "workflow-library",
                    "workflow_id": workflow_id,
                    "task_description": event.get("task_description"),
                    "recommendation_position": event.get("recommendation_position"),
                    "total_recommendations": event.get("total_recommendations"),
                },
            )

            logger.debug(f"Recorded workflow selection: {record_id}")
            return {"learning_record_id": record_id}

        except ImportError:
            logger.debug("Learning system not available, skipping selection recording")
        except Exception as e:
            logger.warning(f"Failed to record workflow selection: {e}")

        return None

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _row_to_summary(self, row) -> Dict[str, Any]:
        """Convert a database row to a workflow summary dict."""
        result = dict(row)
        # Ensure arrays are lists
        for key in ("tags", "node_types", "secondary_categories", "credentials_required"):
            if key in result and result[key] is not None:
                result[key] = list(result[key])
        # Remove search internals
        result.pop("rank", None)
        result.pop("combined_score", None)
        # Convert UUID
        if "id" in result:
            result["id"] = str(result["id"])
        return result
