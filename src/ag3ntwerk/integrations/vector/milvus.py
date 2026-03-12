"""
Milvus Integration for ag3ntwerk.

Provides distributed vector similarity search using Milvus.
Best for large-scale deployments with millions of vectors.

Requirements:
    - Milvus server running (standalone or cluster)
    - pip install pymilvus

Setup:
    docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ag3ntwerk.integrations.vector.base import (
    VectorStore,
    VectorDocument,
    SearchResult,
    EmbeddingProvider,
    DistanceMetric,
)

logger = logging.getLogger(__name__)


class MilvusStore(VectorStore):
    """
    Milvus-based vector store for large-scale deployments.

    Milvus is a distributed vector database designed for billion-scale
    similarity search with high performance.

    Features:
    - Horizontal scaling for massive datasets
    - Multiple index types (HNSW, IVF_FLAT, IVF_SQ8, etc.)
    - Hybrid search (vector + scalar filtering)
    - GPU acceleration support

    Example:
        store = MilvusStore(
            host="localhost",
            port=19530,
            collection_name="agentwerk_knowledge",
            embedding_provider=OllamaEmbeddingProvider(),
        )
        await store.initialize()

        # Add documents
        await store.add_texts(
            texts=["Document 1", "Document 2"],
            metadatas=[{"category": "tech"}, {"category": "finance"}],
        )

        # Search with filtering
        results = await store.search_text(
            "query",
            limit=10,
            filter_metadata={"category": "tech"}
        )
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "agentwerk_vectors",
        embedding_provider: Optional[EmbeddingProvider] = None,
        embedding_dimension: int = 768,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        default_namespace: str = "default",
        index_type: str = "HNSW",
    ):
        """
        Initialize Milvus store.

        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the Milvus collection
            embedding_provider: Provider for generating embeddings
            embedding_dimension: Dimension of embeddings
            distance_metric: Distance metric for similarity
            default_namespace: Default namespace (partition) for documents
            index_type: Index type (HNSW, IVF_FLAT, IVF_SQ8, etc.)
        """
        super().__init__(embedding_provider, default_namespace)

        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.distance_metric = distance_metric
        self.index_type = index_type
        self._collection = None
        self._connected = False

        # Update dimension from provider if available
        if embedding_provider:
            self.embedding_dimension = embedding_provider.dimension

    def _get_metric_type(self) -> str:
        """Get Milvus metric type string."""
        if self.distance_metric == DistanceMetric.COSINE:
            return "COSINE"
        elif self.distance_metric == DistanceMetric.EUCLIDEAN:
            return "L2"
        elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return "IP"
        else:
            return "COSINE"

    async def initialize(self) -> None:
        """Initialize Milvus connection and create collection."""
        from pymilvus import (
            connections,
            Collection,
            FieldSchema,
            CollectionSchema,
            DataType,
            utility,
        )

        # Connect to Milvus
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port,
        )
        self._connected = True

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dimension
            ),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="namespace", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
        ]
        schema = CollectionSchema(fields=fields, description="ag3ntwerk vector documents")

        # Create collection if not exists
        if not utility.has_collection(self.collection_name):
            self._collection = Collection(
                name=self.collection_name,
                schema=schema,
            )
            logger.info(f"Created Milvus collection: {self.collection_name}")
        else:
            self._collection = Collection(name=self.collection_name)
            logger.info(f"Connected to existing Milvus collection: {self.collection_name}")

        # Create index on embedding field
        index_params = self._get_index_params()
        if not self._collection.has_index():
            self._collection.create_index(
                field_name="embedding",
                index_params=index_params,
            )
            logger.info(f"Created {self.index_type} index on embedding field")

        # Load collection into memory for search
        self._collection.load()

    def _get_index_params(self) -> Dict[str, Any]:
        """Get index parameters based on index type."""
        metric_type = self._get_metric_type()

        if self.index_type == "HNSW":
            return {
                "metric_type": metric_type,
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 256},
            }
        elif self.index_type == "IVF_FLAT":
            return {
                "metric_type": metric_type,
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
        elif self.index_type == "IVF_SQ8":
            return {
                "metric_type": metric_type,
                "index_type": "IVF_SQ8",
                "params": {"nlist": 1024},
            }
        else:
            return {
                "metric_type": metric_type,
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 256},
            }

    async def close(self) -> None:
        """Close Milvus connection."""
        from pymilvus import connections

        if self._collection:
            self._collection.release()
            self._collection = None

        if self._connected:
            connections.disconnect("default")
            self._connected = False

    async def add_documents(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None,
    ) -> List[str]:
        """Add documents to Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        # Prepare data for insertion
        ids = []
        contents = []
        embeddings = []
        metadatas = []
        namespaces = []
        created_ats = []

        for doc in documents:
            if doc.embedding is None:
                raise ValueError(f"Document {doc.id} has no embedding")

            ids.append(doc.id)
            contents.append(doc.content[:65535])  # Truncate to max length
            embeddings.append(doc.embedding)
            metadatas.append(json.dumps(doc.metadata)[:65535])
            namespaces.append(ns)
            created_ats.append(doc.created_at.isoformat())

        # Insert data
        self._collection.insert(
            [
                ids,
                contents,
                embeddings,
                metadatas,
                namespaces,
                created_ats,
            ]
        )

        # Flush to ensure persistence
        self._collection.flush()

        logger.debug(f"Added {len(ids)} documents to Milvus")
        return ids

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar documents in Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        # Build filter expression
        expr_parts = [f'namespace == "{ns}"']
        if filter_metadata:
            # Note: Milvus doesn't support JSON field filtering directly
            # We filter in post-processing for complex metadata
            pass

        expr = " && ".join(expr_parts) if expr_parts else None

        # Search parameters
        search_params = {"metric_type": self._get_metric_type()}
        if self.index_type == "HNSW":
            search_params["params"] = {"ef": 128}
        elif self.index_type in ["IVF_FLAT", "IVF_SQ8"]:
            search_params["params"] = {"nprobe": 16}

        # Perform search
        results = self._collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=limit * 2 if filter_metadata else limit,  # Over-fetch for filtering
            expr=expr,
            output_fields=["id", "content", "metadata", "namespace", "created_at"],
        )

        # Process results
        search_results = []
        for hits in results:
            for hit in hits:
                # Calculate similarity score
                distance = hit.distance
                if self.distance_metric == DistanceMetric.COSINE:
                    # Milvus returns 1 - cosine_similarity for COSINE
                    score = 1 - distance
                elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
                    # IP returns negative inner product, higher is better
                    score = -distance
                else:
                    # L2 distance: convert to similarity
                    score = 1 / (1 + distance)

                if score < min_score:
                    continue

                # Parse metadata
                metadata_str = hit.entity.get("metadata", "{}")
                try:
                    metadata = json.loads(metadata_str)
                except json.JSONDecodeError:
                    metadata = {}

                # Apply metadata filter if specified
                if filter_metadata:
                    if not all(metadata.get(k) == v for k, v in filter_metadata.items()):
                        continue

                doc = VectorDocument(
                    id=hit.entity.get("id"),
                    content=hit.entity.get("content", ""),
                    metadata=metadata,
                    namespace=hit.entity.get("namespace", ns),
                )

                search_results.append(
                    SearchResult(
                        document=doc,
                        score=score,
                        distance=distance,
                    )
                )

                if len(search_results) >= limit:
                    break

        return search_results

    async def delete_documents(
        self,
        document_ids: List[str],
        namespace: Optional[str] = None,
    ) -> int:
        """Delete documents by ID from Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        # Build delete expression
        ids_str = ", ".join(f'"{id}"' for id in document_ids)
        expr = f'id in [{ids_str}] && namespace == "{ns}"'

        # Delete
        self._collection.delete(expr)
        self._collection.flush()

        logger.debug(f"Deleted documents from Milvus: {document_ids}")
        return len(document_ids)

    async def get_document(
        self,
        document_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[VectorDocument]:
        """Get a document by ID from Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        # Query by ID
        results = self._collection.query(
            expr=f'id == "{document_id}" && namespace == "{ns}"',
            output_fields=["id", "content", "metadata", "namespace", "created_at"],
        )

        if not results:
            return None

        result = results[0]
        metadata_str = result.get("metadata", "{}")
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}

        return VectorDocument(
            id=result.get("id"),
            content=result.get("content", ""),
            metadata=metadata,
            namespace=result.get("namespace", ns),
        )

    async def count_documents(self, namespace: Optional[str] = None) -> int:
        """Count documents in Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        ns = namespace or self.default_namespace

        results = self._collection.query(
            expr=f'namespace == "{ns}"',
            output_fields=["id"],
        )

        return len(results)

    async def list_namespaces(self) -> List[str]:
        """List all namespaces in Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        # Query all unique namespaces
        results = self._collection.query(
            expr="namespace != ''",
            output_fields=["namespace"],
        )

        namespaces = set(r.get("namespace") for r in results if r.get("namespace"))
        return sorted(list(namespaces))

    async def delete_namespace(self, namespace: str) -> int:
        """Delete all documents in a namespace."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        # Count first
        count = await self.count_documents(namespace)

        # Delete all in namespace
        self._collection.delete(f'namespace == "{namespace}"')
        self._collection.flush()

        logger.info(f"Deleted namespace {namespace} with {count} documents from Milvus")
        return count

    async def create_partition(self, partition_name: str) -> None:
        """Create a partition (namespace) in Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        if not self._collection.has_partition(partition_name):
            self._collection.create_partition(partition_name)
            logger.info(f"Created Milvus partition: {partition_name}")

    async def drop_partition(self, partition_name: str) -> None:
        """Drop a partition from Milvus."""
        if not self._collection:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        if self._collection.has_partition(partition_name):
            self._collection.drop_partition(partition_name)
            logger.info(f"Dropped Milvus partition: {partition_name}")
