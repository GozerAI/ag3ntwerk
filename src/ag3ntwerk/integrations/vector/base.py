"""
Base classes for vector database integrations.

Provides abstract interfaces for vector storage and retrieval.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    """
    A document with vector embedding for similarity search.

    Attributes:
        id: Unique document identifier
        content: Original text content
        embedding: Vector representation of the content
        metadata: Additional metadata (source, timestamp, tags, etc.)
        namespace: Optional namespace for multi-tenant separation
    """

    content: str
    embedding: Optional[List[float]] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "namespace": self.namespace,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorDocument":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid4())),
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            namespace=data.get("namespace", "default"),
            created_at=created_at or datetime.now(timezone.utc),
        )


@dataclass
class SearchResult:
    """
    Result from a vector similarity search.

    Attributes:
        document: The matching document
        score: Similarity score (higher is more similar, typically 0-1)
        distance: Distance metric (lower is closer)
    """

    document: VectorDocument
    score: float
    distance: Optional[float] = None

    @property
    def similarity(self) -> float:
        """Alias for score, representing similarity percentage."""
        return self.score


class DistanceMetric(Enum):
    """Distance metrics for vector similarity."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    Embedding providers convert text content into vector representations.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced by this provider."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Vector embedding as list of floats
        """
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector embeddings
        """
        pass


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider using Ollama's embedding models.

    Example:
        provider = OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )
        embedding = await provider.embed_text("Hello world")
    """

    # Common embedding model dimensions
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimension = self.MODEL_DIMENSIONS.get(model, 768)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Ollama doesn't have batch embedding, so we process sequentially
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider using OpenAI's embedding API.

    Requires OPENAI_API_KEY environment variable.

    Example:
        provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")
        embedding = await provider.embed_text("Hello world")
    """

    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
    ):
        import os

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self._dimension = self.MODEL_DIMENSIONS.get(model, 1536)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI batch API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]


class VectorStore(ABC):
    """
    Abstract base class for vector stores.

    Vector stores provide persistence and similarity search for embeddings.

    Example:
        store = PgVectorStore(connection_string="postgresql://...")
        await store.initialize()

        # Add documents
        doc = VectorDocument(content="Hello world", embedding=[0.1, 0.2, ...])
        await store.add_documents([doc])

        # Search
        results = await store.search(query_embedding=[0.1, 0.2, ...], limit=5)
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        default_namespace: str = "default",
    ):
        """
        Initialize vector store.

        Args:
            embedding_provider: Provider for generating embeddings
            default_namespace: Default namespace for documents
        """
        self.embedding_provider = embedding_provider
        self.default_namespace = default_namespace

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store (create tables, indexes, etc.)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        pass

    @abstractmethod
    async def add_documents(
        self,
        documents: List[VectorDocument],
        namespace: Optional[str] = None,
    ) -> List[str]:
        """
        Add documents to the store.

        Args:
            documents: Documents to add (embeddings must be set)
            namespace: Optional namespace override

        Returns:
            List of document IDs that were added
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query vector
            limit: Maximum results to return
            namespace: Namespace to search in
            filter_metadata: Metadata filters to apply
            min_score: Minimum similarity score threshold

        Returns:
            List of search results ordered by similarity
        """
        pass

    @abstractmethod
    async def delete_documents(
        self,
        document_ids: List[str],
        namespace: Optional[str] = None,
    ) -> int:
        """
        Delete documents by ID.

        Args:
            document_ids: IDs of documents to delete
            namespace: Namespace containing the documents

        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    async def get_document(
        self,
        document_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[VectorDocument]:
        """
        Get a document by ID.

        Args:
            document_id: Document ID
            namespace: Namespace containing the document

        Returns:
            Document if found, None otherwise
        """
        pass

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        namespace: Optional[str] = None,
    ) -> List[str]:
        """
        Add texts to the store, automatically generating embeddings.

        Args:
            texts: Text content to add
            metadatas: Optional metadata for each text
            namespace: Optional namespace

        Returns:
            List of document IDs

        Raises:
            ValueError: If no embedding provider is configured
        """
        if not self.embedding_provider:
            raise ValueError("No embedding provider configured")

        # Generate embeddings
        embeddings = await self.embedding_provider.embed_texts(texts)

        # Create documents
        documents = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            doc = VectorDocument(
                content=text,
                embedding=embedding,
                metadata=metadata,
                namespace=namespace or self.default_namespace,
            )
            documents.append(doc)

        return await self.add_documents(documents, namespace)

    async def search_text(
        self,
        query: str,
        limit: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search using text query, automatically generating embedding.

        Args:
            query: Text query
            limit: Maximum results
            namespace: Namespace to search
            filter_metadata: Metadata filters
            min_score: Minimum similarity threshold

        Returns:
            Search results

        Raises:
            ValueError: If no embedding provider is configured
        """
        if not self.embedding_provider:
            raise ValueError("No embedding provider configured")

        query_embedding = await self.embedding_provider.embed_text(query)
        return await self.search(
            query_embedding=query_embedding,
            limit=limit,
            namespace=namespace,
            filter_metadata=filter_metadata,
            min_score=min_score,
        )

    async def count_documents(self, namespace: Optional[str] = None) -> int:
        """
        Count documents in a namespace.

        Args:
            namespace: Namespace to count (or default)

        Returns:
            Document count
        """
        # Default implementation - subclasses can override for efficiency
        raise NotImplementedError("Subclass must implement count_documents")

    async def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the store.

        Returns:
            List of namespace names
        """
        raise NotImplementedError("Subclass must implement list_namespaces")

    async def delete_namespace(self, namespace: str) -> int:
        """
        Delete all documents in a namespace.

        Args:
            namespace: Namespace to delete

        Returns:
            Number of documents deleted
        """
        raise NotImplementedError("Subclass must implement delete_namespace")
