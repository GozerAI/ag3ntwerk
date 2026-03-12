"""
Qdrant Integration for ag3ntwerk.

Provides vector similarity search using Qdrant vector database.
Best for production deployments with advanced filtering capabilities.

Requirements:
    - Qdrant server running (local or cloud)
    - pip install qdrant-client

Setup:
    docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ag3ntwerk.integrations.vector.base import (
    VectorStore,
    VectorDocument,
    SearchResult,
    EmbeddingProvider,
    DistanceMetric,
)

logger = logging.getLogger(__name__)


class QdrantStore(VectorStore):
    """
    Qdrant-based vector store for production deployments.

    Qdrant is a vector similarity search engine with extended filtering
    support and a focus on production readiness.

    Features:
    - Rich payload filtering with multiple field types
    - Quantization for memory efficiency
    - Distributed deployment support
    - Built-in recommendation API

    Example:
        store = QdrantStore(
            host="localhost",
            port=6333,
            collection_name="csuite_knowledge",
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
        port: int = 6333,
        grpc_port: int = 6334,
        collection_name: str = "csuite_vectors",
        embedding_provider: Optional[EmbeddingProvider] = None,
        embedding_dimension: int = 768,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        default_namespace: str = "default",
        use_grpc: bool = False,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Initialize Qdrant store.

        Args:
            host: Qdrant server host
            port: Qdrant REST API port
            grpc_port: Qdrant gRPC port
            collection_name: Name of the Qdrant collection
            embedding_provider: Provider for generating embeddings
            embedding_dimension: Dimension of embeddings
            distance_metric: Distance metric for similarity
            default_namespace: Default namespace for documents
            use_grpc: Whether to use gRPC instead of REST
            api_key: API key for Qdrant Cloud
            url: Full URL for Qdrant Cloud (overrides host/port)
        """
        super().__init__(embedding_provider, default_namespace)

        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.distance_metric = distance_metric
        self.use_grpc = use_grpc
        self.api_key = api_key
        self.url = url
        self._client = None

        # Update dimension from provider if available
        if embedding_provider:
            self.embedding_dimension = embedding_provider.dimension

    def _get_distance(self):
        """Get Qdrant distance type."""
        from qdrant_client.models import Distance

        if self.distance_metric == DistanceMetric.COSINE:
            return Distance.COSINE
        elif self.distance_metric == DistanceMetric.EUCLIDEAN:
            return Distance.EUCLID
        elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
            return Distance.DOT
        else:
            return Distance.COSINE

    async def initialize(self) -> None:
        """Initialize Qdrant client and create collection."""
        from qdrant_client import QdrantClient
        from qdrant_client.models import VectorParams

        # Create client
        if self.url:
            # Qdrant Cloud
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                prefer_grpc=self.use_grpc,
            )
        else:
            # Local Qdrant
            self._client = QdrantClient(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.use_grpc,
                api_key=self.api_key,
            )

        # Check if collection exists
        collections = self._client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            # Create collection
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=self._get_distance(),
                ),
            )
            logger.info(f"Created Qdrant collection: {self.collection_name}")
        else:
            logger.info(f"Connected to existing Qdrant collection: {self.collection_name}")

    async def close(self) -> None:
        """Close Qdrant client."""
        if self._client:
            self._client.close()
            self._client = None

    async def add_documents(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None,
    ) -> List[str]:
        """Add documents to Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import PointStruct

        ns = namespace or self.default_namespace

        points = []
        ids = []

        for doc in documents:
            if doc.embedding is None:
                raise ValueError(f"Document {doc.id} has no embedding")

            # Create payload with metadata and namespace
            payload = {
                "content": doc.content,
                "namespace": ns,
                "created_at": doc.created_at.isoformat(),
                **doc.metadata,
            }

            # Use UUID for point ID (Qdrant supports string IDs)
            point_id = doc.id

            points.append(
                PointStruct(
                    id=point_id,
                    vector=doc.embedding,
                    payload=payload,
                )
            )
            ids.append(doc.id)

        # Upsert points
        self._client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.debug(f"Added {len(ids)} documents to Qdrant")
        return ids

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar documents in Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        ns = namespace or self.default_namespace

        # Build filter
        must_conditions = [
            FieldCondition(
                key="namespace",
                match=MatchValue(value=ns),
            )
        ]

        if filter_metadata:
            for key, value in filter_metadata.items():
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        query_filter = Filter(must=must_conditions)

        # Search
        results = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=min_score,
        )

        # Convert to SearchResult
        search_results = []
        for hit in results:
            payload = hit.payload or {}

            # Extract standard fields
            content = payload.pop("content", "")
            namespace_val = payload.pop("namespace", ns)
            created_at = payload.pop("created_at", None)

            # Remaining payload is metadata
            metadata = payload

            doc = VectorDocument(
                id=str(hit.id),
                content=content,
                metadata=metadata,
                namespace=namespace_val,
            )

            # Calculate distance from score
            if self.distance_metric == DistanceMetric.COSINE:
                distance = 1 - hit.score
            elif self.distance_metric == DistanceMetric.DOT_PRODUCT:
                distance = -hit.score
            else:
                distance = hit.score

            search_results.append(
                SearchResult(
                    document=doc,
                    score=hit.score,
                    distance=distance,
                )
            )

        return search_results

    async def delete_documents(
        self,
        document_ids: List[str],
        namespace: Optional[str] = None,
    ) -> int:
        """Delete documents by ID from Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import PointIdsList

        # Delete by IDs
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=document_ids),
        )

        logger.debug(f"Deleted documents from Qdrant: {document_ids}")
        return len(document_ids)

    async def get_document(
        self,
        document_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[VectorDocument]:
        """Get a document by ID from Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        # Retrieve point
        results = self._client.retrieve(
            collection_name=self.collection_name,
            ids=[document_id],
            with_payload=True,
        )

        if not results:
            return None

        point = results[0]
        payload = point.payload or {}

        ns = namespace or self.default_namespace

        # Extract standard fields
        content = payload.pop("content", "")
        namespace_val = payload.pop("namespace", ns)
        created_at = payload.pop("created_at", None)

        return VectorDocument(
            id=str(point.id),
            content=content,
            metadata=payload,
            namespace=namespace_val,
        )

    async def count_documents(self, namespace: Optional[str] = None) -> int:
        """Count documents in Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        ns = namespace or self.default_namespace

        # Count with filter
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="namespace",
                    match=MatchValue(value=ns),
                )
            ]
        )

        result = self._client.count(
            collection_name=self.collection_name,
            count_filter=query_filter,
            exact=True,
        )

        return result.count

    async def list_namespaces(self) -> List[str]:
        """List all namespaces in Qdrant."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        # Scroll through all points to get unique namespaces
        namespaces = set()

        offset = None
        while True:
            results, next_offset = self._client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["namespace"],
            )

            for point in results:
                if point.payload and "namespace" in point.payload:
                    namespaces.add(point.payload["namespace"])

            if next_offset is None:
                break
            offset = next_offset

        return sorted(list(namespaces))

    async def delete_namespace(self, namespace: str) -> int:
        """Delete all documents in a namespace."""
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Count first
        count = await self.count_documents(namespace)

        # Delete by filter
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace),
                    )
                ]
            ),
        )

        logger.info(f"Deleted namespace {namespace} with {count} documents from Qdrant")
        return count

    async def create_payload_index(
        self,
        field_name: str,
        field_type: str = "keyword",
    ) -> None:
        """
        Create a payload index for faster filtering.

        Args:
            field_name: Name of the payload field to index
            field_type: Type of index (keyword, integer, float, geo, text)
        """
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import PayloadSchemaType

        type_map = {
            "keyword": PayloadSchemaType.KEYWORD,
            "integer": PayloadSchemaType.INTEGER,
            "float": PayloadSchemaType.FLOAT,
            "geo": PayloadSchemaType.GEO,
            "text": PayloadSchemaType.TEXT,
        }

        schema_type = type_map.get(field_type, PayloadSchemaType.KEYWORD)

        self._client.create_payload_index(
            collection_name=self.collection_name,
            field_name=field_name,
            field_schema=schema_type,
        )

        logger.info(f"Created payload index on {field_name} ({field_type})")

    async def recommend(
        self,
        positive_ids: List[str],
        negative_ids: Optional[List[str]] = None,
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Get recommendations based on positive and negative examples.

        This is a unique Qdrant feature for recommendation systems.

        Args:
            positive_ids: IDs of documents to recommend similar to
            negative_ids: IDs of documents to recommend dissimilar to
            limit: Maximum results to return
            namespace: Namespace to search in
            filter_metadata: Additional metadata filters

        Returns:
            List of recommended documents
        """
        if not self._client:
            raise RuntimeError("Store not initialized. Call initialize() first.")

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        ns = namespace or self.default_namespace

        # Build filter
        must_conditions = [
            FieldCondition(
                key="namespace",
                match=MatchValue(value=ns),
            )
        ]

        if filter_metadata:
            for key, value in filter_metadata.items():
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        query_filter = Filter(must=must_conditions)

        # Recommend
        results = self._client.recommend(
            collection_name=self.collection_name,
            positive=positive_ids,
            negative=negative_ids or [],
            query_filter=query_filter,
            limit=limit,
        )

        # Convert to SearchResult
        search_results = []
        for hit in results:
            payload = hit.payload or {}

            content = payload.pop("content", "")
            namespace_val = payload.pop("namespace", ns)
            created_at = payload.pop("created_at", None)

            doc = VectorDocument(
                id=str(hit.id),
                content=content,
                metadata=payload,
                namespace=namespace_val,
            )

            search_results.append(
                SearchResult(
                    document=doc,
                    score=hit.score,
                    distance=(
                        1 - hit.score
                        if self.distance_metric == DistanceMetric.COSINE
                        else hit.score
                    ),
                )
            )

        return search_results
