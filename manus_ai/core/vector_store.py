"""
Vector Store Integration for Semantic Search and RAG
Supports Qdrant for high-performance vector operations
"""

import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, PointStruct,
        Filter, FieldCondition, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document with metadata for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SearchResult:
    """Search result with relevance score"""
    document: Document
    score: float
    rank: int


class EmbeddingModel:
    """Handles text embeddings using sentence transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model

        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2, 384 dims)
        """
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Loaded embedding model: {model_name} (dimension: {self.dimension})")

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings"""
        return self.model.encode(texts, convert_to_numpy=True)

    def encode_single(self, text: str) -> List[float]:
        """Encode single text to embedding"""
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()


class VectorStore:
    """Vector store for semantic search and RAG"""

    def __init__(
        self,
        collection_name: str = "manus_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        use_memory: bool = False
    ):
        """
        Initialize vector store

        Args:
            collection_name: Name of the vector collection
            embedding_model: Sentence transformer model name
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            use_memory: Use in-memory storage (for testing)
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client not installed. Run: pip install qdrant-client")

        self.collection_name = collection_name
        self.use_memory = use_memory

        # Initialize embedding model
        self.embedder = EmbeddingModel(embedding_model)

        # Initialize Qdrant client
        if use_memory:
            self.client = QdrantClient(":memory:")
            logger.info("Using in-memory Qdrant")
        else:
            self.client = QdrantClient(host=qdrant_url, port=qdrant_port)
            logger.info(f"Connected to Qdrant at {qdrant_url}:{qdrant_port}")

        # Create collection if it doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure collection exists with correct configuration"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedder.dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Collection already exists: {self.collection_name}")

    def _generate_id(self, content: str) -> str:
        """Generate deterministic ID from content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def add_documents(
        self,
        documents: List[Document],
        batch_size: int = 100
    ) -> int:
        """
        Add documents to vector store

        Args:
            documents: List of documents to add
            batch_size: Batch size for upload

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        # Generate embeddings
        contents = [doc.content for doc in documents]
        embeddings = self.embedder.encode(contents)

        # Create points for Qdrant
        points = []
        for doc, embedding in zip(documents, embeddings):
            doc_id = doc.id or self._generate_id(doc.content)

            points.append(
                PointStruct(
                    id=doc_id,
                    vector=embedding.tolist(),
                    payload={
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "timestamp": doc.timestamp.isoformat() if doc.timestamp else None
                    }
                )
            )

        # Upload in batches
        total_uploaded = 0
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            total_uploaded += len(batch)
            logger.debug(f"Uploaded batch {i//batch_size + 1}: {len(batch)} documents")

        logger.info(f"Added {total_uploaded} documents to {self.collection_name}")
        return total_uploaded

    async def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Semantic search for similar documents

        Args:
            query: Search query
            limit: Maximum number of results
            score_threshold: Minimum relevance score (0-1)
            filters: Metadata filters

        Returns:
            List of search results sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.embedder.encode_single(query)

        # Build filters if provided
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                )
            if conditions:
                qdrant_filter = Filter(must=conditions)

        # Search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter
        )

        # Convert to SearchResult objects
        results = []
        for rank, result in enumerate(search_results, 1):
            doc = Document(
                id=str(result.id),
                content=result.payload["content"],
                metadata=result.payload["metadata"],
                timestamp=datetime.fromisoformat(result.payload["timestamp"]) if result.payload.get("timestamp") else None
            )
            results.append(SearchResult(
                document=doc,
                score=result.score,
                rank=rank
            ))

        logger.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results

    async def retrieve_context(
        self,
        query: str,
        max_tokens: int = 2000,
        limit: int = 10
    ) -> Tuple[str, List[SearchResult]]:
        """
        Retrieve relevant context for RAG

        Args:
            query: User query
            max_tokens: Maximum context tokens (approximate)
            limit: Maximum documents to retrieve

        Returns:
            Tuple of (formatted_context, search_results)
        """
        results = await self.search(query, limit=limit)

        # Build context within token limit (rough estimate: 4 chars = 1 token)
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4
        used_results = []

        for result in results:
            content = result.document.content
            if total_chars + len(content) > max_chars:
                break

            context_parts.append(f"[Source {result.rank}, Score: {result.score:.2f}]\n{content}")
            total_chars += len(content)
            used_results.append(result)

        context = "\n\n".join(context_parts)
        logger.info(f"Retrieved {len(used_results)} documents for context ({total_chars} chars)")

        return context, used_results

    def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} documents")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    def clear_collection(self) -> bool:
        """Clear all documents from collection"""
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
            logger.info(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "embedding_dimension": self.embedder.dimension,
                "embedding_model": self.embedder.model_name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


class RAGSystem:
    """Retrieval-Augmented Generation system"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.logger = logging.getLogger(__name__)

    async def generate_with_context(
        self,
        query: str,
        llm_generate_func,
        max_context_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response using RAG

        Args:
            query: User query
            llm_generate_func: Async function to generate LLM response
            max_context_tokens: Maximum tokens for retrieved context
            system_prompt: Optional system prompt

        Returns:
            Dictionary with response and sources
        """
        # Retrieve relevant context
        context, sources = await self.vector_store.retrieve_context(
            query,
            max_tokens=max_context_tokens
        )

        if not context:
            self.logger.warning("No relevant context found")
            context = "No relevant information found in knowledge base."

        # Build RAG prompt
        rag_prompt = f"""You are answering based on the following relevant information from the knowledge base:

{context}

User Question: {query}

Please provide a comprehensive answer based on the retrieved information. If the information is insufficient, acknowledge this limitation."""

        # Generate response
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": rag_prompt})

        response = await llm_generate_func(messages)

        return {
            "response": response,
            "sources": [
                {
                    "content": src.document.content,
                    "score": src.score,
                    "rank": src.rank,
                    "metadata": src.document.metadata
                }
                for src in sources
            ],
            "context_used": context
        }
