"""
pgvector Integration for ag3ntwerk.

Provides vector similarity search using PostgreSQL with the pgvector extension.
This integrates with ag3ntwerk's existing PostgreSQL persistence layer.

Requirements:
    - PostgreSQL with pgvector extension installed
    - pip install asyncpg

Setup:
    CREATE EXTENSION IF NOT EXISTS vector;
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ag3ntwerk.integrations.vector.base import (
    VectorStore,
    VectorDocument,
    SearchResult,
    EmbeddingProvider,
    DistanceMetric,
)

logger = logging.getLogger(__name__)

# Valid identifier pattern for PostgreSQL table/index names
_VALID_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, identifier_type: str = "identifier") -> str:
    """
    Validate that a name is a safe PostgreSQL identifier.

    Args:
        name: The identifier to validate
        identifier_type: Type of identifier for error messages

    Returns:
        The validated identifier

    Raises:
        ValueError: If the identifier contains unsafe characters
    """
    if not _VALID_IDENTIFIER.match(name):
        raise ValueError(
            f"Invalid {identifier_type}: '{name}'. "
            f"Must start with letter or underscore and contain only alphanumeric characters and underscores."
        )
    if len(name) > 63:  # PostgreSQL identifier limit
        raise ValueError(f"{identifier_type} too long: '{name}'. Maximum 63 characters.")
    return name


class PgVectorStore(VectorStore):
    """
    PostgreSQL-based vector store using pgvector extension.

    This store uses the existing ag3ntwerk PostgreSQL infrastructure,
    adding vector search capabilities without additional services.

    Features:
    - Cosine similarity, Euclidean distance, inner product
    - HNSW and IVFFlat indexes for fast approximate search
    - Metadata filtering with JSONB
    - Namespace isolation

    Example:
        store = PgVectorStore(
            connection_string="postgresql://user:pass@localhost/ag3ntwerk",
            embedding_provider=OllamaEmbeddingProvider(),
        )
        await store.initialize()

        # Add documents
        await store.add_texts(
            texts=["Document 1", "Document 2"],
            metadatas=[{"source": "web"}, {"source": "file"}],
            namespace="knowledge_base"
        )

        # Search
        results = await store.search_text("query", limit=5)
        for result in results:
            print(f"{result.score:.2f}: {result.document.content}")
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        table_name: str = "vector_documents",
        embedding_dimension: int = 768,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        default_namespace: str = "default",
    ):
        """
        Initialize pgvector store.

        Args:
            connection_string: PostgreSQL connection string
            embedding_provider: Provider for generating embeddings
            table_name: Name of the vector table
            embedding_dimension: Dimension of embeddings
            distance_metric: Distance metric for similarity
            default_namespace: Default namespace for documents
        """
        super().__init__(embedding_provider, default_namespace)

        import os

        self.connection_string = connection_string or os.environ.get(
            "AGENTWERK_DB_URL", "postgresql://localhost/ag3ntwerk"
        )
        # Validate table name to prevent SQL injection
        self.table_name = _validate_identifier(table_name, "table name")
        self.embedding_dimension = embedding_dimension
        self.distance_metric = distance_metric
        self._pool = None

        # Update dimension from provider if available
        if embedding_provider:
            self.embedding_dimension = embedding_provider.dimension

    async def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        import asyncpg

        self._pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10,
        )

        async with self._pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create table for vector documents
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dimension}),
                    metadata JSONB DEFAULT '{{}}',
                    namespace TEXT DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """
            )

            # Create index on namespace for filtering
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_namespace
                ON {self.table_name}(namespace)
            """
            )

            # Create HNSW index for fast approximate nearest neighbor search
            # Using cosine distance by default
            index_ops = self._get_index_ops()
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
                ON {self.table_name}
                USING hnsw (embedding {index_ops})
                WITH (m = 16, ef_construction = 64)
            """
            )

            # Create GIN index on metadata for filtering
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_metadata
                ON {self.table_name}
                USING GIN (metadata)
            """
            )

        logger.info(f"Initialized pgvector store: {self.table_name}")

    def _get_index_ops(self) -> str:
        """Get index operator class for the distance metric."""
        if self.distance_metric == DistanceMetric.COSINE:
            return "vector_cosine_ops"
        elif self.distance_metric == DistanceMetric.EUCLIDEAN:
            return "vector_l2_ops"
        elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return "vector_ip_ops"
        else:
            return "vector_cosine_ops"

    def _get_distance_operator(self) -> str:
        """Get the distance operator for queries."""
        if self.distance_metric == DistanceMetric.COSINE:
            return "<=>"  # Cosine distance
        elif self.distance_metric == DistanceMetric.EUCLIDEAN:
            return "<->"  # L2 distance
        elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return "<#>"  # Negative inner product
        else:
            return "<=>"

    async def close(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def add_documents(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None,
    ) -> List[str]:
        """Add documents to the store."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace
        ids = []

        async with self._pool.acquire() as conn:
            for doc in documents:
                if doc.embedding is None:
                    raise ValueError(f"Document {doc.id} has no embedding")

                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(str(x) for x in doc.embedding)}]"

                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (id, content, embedding, metadata, namespace, created_at)
                    VALUES ($1, $2, $3::vector, $4, $5, $6)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        namespace = EXCLUDED.namespace
                """,
                    doc.id,
                    doc.content,
                    embedding_str,
                    json.dumps(doc.metadata),
                    ns,
                    doc.created_at,
                )
                ids.append(doc.id)

        logger.debug(f"Added {len(ids)} documents to pgvector")
        return ids

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace
        distance_op = self._get_distance_operator()
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Build query with optional metadata filter
        query = f"""
            SELECT
                id, content, metadata, namespace, created_at,
                embedding {distance_op} $1::vector AS distance
            FROM {self.table_name}
            WHERE namespace = $2
        """
        params = [embedding_str, ns]

        if filter_metadata:
            query += " AND metadata @> $3::jsonb"
            params.append(json.dumps(filter_metadata))

        # For cosine distance, convert to similarity score
        if self.distance_metric == DistanceMetric.COSINE:
            # Cosine distance is in [0, 2], similarity = 1 - distance/2
            query += f" HAVING (1 - (embedding {distance_op} $1::vector) / 2) >= ${len(params) + 1}"
        else:
            query += f" HAVING 1 / (1 + (embedding {distance_op} $1::vector)) >= ${len(params) + 1}"

        params.append(min_score)

        query += f"""
            ORDER BY distance ASC
            LIMIT ${len(params) + 1}
        """
        params.append(limit)

        results = []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            for row in rows:
                # Calculate similarity score from distance
                distance = row["distance"]
                if self.distance_metric == DistanceMetric.COSINE:
                    # Cosine distance to similarity: 1 - distance/2
                    score = 1 - (distance / 2)
                else:
                    # Generic conversion
                    score = 1 / (1 + distance)

                doc = VectorDocument(
                    id=row["id"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    namespace=row["namespace"],
                    created_at=row["created_at"],
                )

                results.append(
                    SearchResult(
                        document=doc,
                        score=score,
                        distance=distance,
                    )
                )

        return results

    async def delete_documents(
        self,
        document_ids: List[str],
        namespace: Optional[str] = None,
    ) -> int:
        """Delete documents by ID."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM {self.table_name}
                WHERE id = ANY($1) AND namespace = $2
            """,
                document_ids,
                ns,
            )

            # Parse "DELETE N" result - result format is "DELETE <count>"
            try:
                count = int(result.split()[-1])
            except (ValueError, IndexError):
                logger.warning(f"Could not parse delete result: {result}")
                count = 0

        logger.debug(f"Deleted {count} documents from pgvector")
        return count

    async def get_document(
        self,
        document_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[VectorDocument]:
        """Get a document by ID."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT id, content, metadata, namespace, created_at
                FROM {self.table_name}
                WHERE id = $1 AND namespace = $2
            """,
                document_id,
                ns,
            )

            if not row:
                return None

            return VectorDocument(
                id=row["id"],
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                namespace=row["namespace"],
                created_at=row["created_at"],
            )

    async def count_documents(self, namespace: Optional[str] = None) -> int:
        """Count documents in a namespace."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                f"""
                SELECT COUNT(*) FROM {self.table_name}
                WHERE namespace = $1
            """,
                ns,
            )

        return result or 0

    async def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT DISTINCT namespace FROM {self.table_name}
                ORDER BY namespace
            """
            )

        return [row["namespace"] for row in rows]

    async def delete_namespace(self, namespace: str) -> int:
        """Delete all documents in a namespace."""
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM {self.table_name}
                WHERE namespace = $1
            """,
                namespace,
            )

            # Parse "DELETE N" result - result format is "DELETE <count>"
            try:
                count = int(result.split()[-1])
            except (ValueError, IndexError):
                logger.warning(f"Could not parse delete result: {result}")
                count = 0

        logger.info(f"Deleted namespace {namespace} with {count} documents")
        return count

    async def update_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None,
        merge: bool = True,
    ) -> bool:
        """
        Update document metadata.

        Args:
            document_id: Document to update
            metadata: New metadata
            namespace: Document namespace
            merge: If True, merge with existing; if False, replace

        Returns:
            True if document was updated
        """
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        async with self._pool.acquire() as conn:
            if merge:
                result = await conn.execute(
                    f"""
                    UPDATE {self.table_name}
                    SET metadata = metadata || $1::jsonb
                    WHERE id = $2 AND namespace = $3
                """,
                    json.dumps(metadata),
                    document_id,
                    ns,
                )
            else:
                result = await conn.execute(
                    f"""
                    UPDATE {self.table_name}
                    SET metadata = $1::jsonb
                    WHERE id = $2 AND namespace = $3
                """,
                    json.dumps(metadata),
                    document_id,
                    ns,
                )

            return "UPDATE 1" in result

    async def search_by_metadata(
        self,
        filter_metadata: Dict[str, Any],
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> List[VectorDocument]:
        """
        Search documents by metadata without vector similarity.

        Args:
            filter_metadata: Metadata filter (JSONB containment)
            namespace: Namespace to search
            limit: Maximum results

        Returns:
            List of matching documents
        """
        if not self._pool:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, content, metadata, namespace, created_at
                FROM {self.table_name}
                WHERE namespace = $1 AND metadata @> $2::jsonb
                ORDER BY created_at DESC
                LIMIT $3
            """,
                ns,
                json.dumps(filter_metadata),
                limit,
            )

            return [
                VectorDocument(
                    id=row["id"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    namespace=row["namespace"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
