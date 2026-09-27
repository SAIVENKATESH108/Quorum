"""RAG Subsystem package exports."""

from src.services.rag.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProvider,
    EmbeddingProviderError,
    GeminiEmbeddingProvider,
    get_default_embedding_provider,
)
from src.services.rag.vector_store import (
    PgVectorStoreProvider,
    RetrievedChunk,
    VectorStoreProvider,
)
from src.services.rag.indexer import ReportIndexer
from src.services.rag.chat_engine import (
    ChatCitation,
    SwarmChatEngine,
    SwarmChatResult,
    ABSTENTION_TEXT,
)

__all__ = [
    "EmbeddingDimensionError",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "GeminiEmbeddingProvider",
    "get_default_embedding_provider",
    "VectorStoreProvider",
    "PgVectorStoreProvider",
    "RetrievedChunk",
    "ReportIndexer",
    "ChatCitation",
    "SwarmChatEngine",
    "SwarmChatResult",
    "ABSTENTION_TEXT",
]
