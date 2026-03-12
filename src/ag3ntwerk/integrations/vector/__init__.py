"""
Vector Database Integrations for ag3ntwerk.

This package provides vector database integrations for:
- Semantic search and retrieval
- RAG (Retrieval Augmented Generation) capabilities
- Knowledge management for Index/CKO agents
- Research embeddings for Axiom agent

Supported backends:
- pgvector: PostgreSQL extension for vector similarity search
- Milvus: Distributed vector database for large-scale deployments
- Qdrant: Fast vector database with filtering support
"""

from ag3ntwerk.integrations.vector.base import (
    VectorStore,
    VectorDocument,
    SearchResult,
    EmbeddingProvider,
)
from ag3ntwerk.integrations.vector.pgvector import PgVectorStore
from ag3ntwerk.integrations.vector.milvus import MilvusStore
from ag3ntwerk.integrations.vector.qdrant import QdrantStore

__all__ = [
    # Base classes
    "VectorStore",
    "VectorDocument",
    "SearchResult",
    "EmbeddingProvider",
    # Implementations
    "PgVectorStore",
    "MilvusStore",
    "QdrantStore",
]
