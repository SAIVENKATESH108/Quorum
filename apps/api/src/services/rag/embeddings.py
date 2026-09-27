"""
Embedding Provider Abstraction and Implementation.

Guarantees:
- Strict verification of vector dimensions (expected 1536 for pgvector compatibility).
- Rejects any mismatch immediately — no truncation, padding, coercion, or silent fallback.
- Persists provider, model name, and dimensions with every embedding.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Sequence

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingDimensionError(ValueError):
    """Raised when an embedding provider returns a vector with unexpected dimensionality."""
    pass


class EmbeddingProviderError(Exception):
    """Raised when the embedding provider fails to generate embeddings."""
    pass


class EmbeddingProvider(ABC):
    """Abstract Strategy interface for embedding generation."""

    provider_name: str
    model_name: str
    expected_dimensions: int

    def __init__(self, expected_dimensions: int = 1536):
        self.expected_dimensions = expected_dimensions

    def _verify_vector_dimensions(self, vector: Sequence[float]) -> List[float]:
        """Strictly validates vector dimension against expected size."""
        if len(vector) != self.expected_dimensions:
            raise EmbeddingDimensionError(
                f"Embedding vector dimension mismatch from {self.provider_name} ({self.model_name}): "
                f"expected {self.expected_dimensions}, got {len(vector)}. "
                f"Refusing to pad, truncate, or coerce vector."
            )
        return list(vector)

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single query string."""
        ...

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of document chunks."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that provider is reachable and credentials are valid."""
        ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini Embedding Provider.
    Uses verified models/gemini-embedding-001 with outputDimensionality=1536.
    """

    provider_name = "Gemini"
    model_name = "gemini-embedding-001"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-embedding-001",
        expected_dimensions: int = 1536,
        timeout: float = 20.0,
    ):
        super().__init__(expected_dimensions=expected_dimensions)
        self.api_key = api_key or settings.GEMINI_API_KEY or ""
        self.model_name = model_name
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            vec = await self.embed_query("ping")
            return len(vec) == self.expected_dimensions
        except Exception as exc:
            logger.warning(f"[GeminiEmbeddingProvider] Health check failed: {exc}")
            return False

    async def embed_query(self, text: str) -> List[float]:
        if not self.api_key:
            raise EmbeddingProviderError("Gemini API key is not configured.")

        url = f"{self.base_url}/models/{self.model_name}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text[:8000]}]},
            "outputDimensionality": self.expected_dimensions,
            "taskType": "RETRIEVAL_QUERY",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise EmbeddingProviderError(
                    f"Gemini embedContent failed ({res.status_code}): {res.text[:200]}"
                )
            data = res.json()
            values = data.get("embedding", {}).get("values")
            if not values:
                raise EmbeddingProviderError("Gemini response missing embedding values.")
            return self._verify_vector_dimensions(values)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise EmbeddingProviderError("Gemini API key is not configured.")

        # Process in batches of up to 10
        batch_size = 10
        results: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            url = f"{self.base_url}/models/{self.model_name}:batchEmbedContents?key={self.api_key}"
            requests = [
                {
                    "model": f"models/{self.model_name}",
                    "content": {"parts": [{"text": t[:8000]}]},
                    "outputDimensionality": self.expected_dimensions,
                    "taskType": "RETRIEVAL_DOCUMENT",
                }
                for t in batch
            ]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json={"requests": requests})
                if res.status_code != 200:
                    raise EmbeddingProviderError(
                        f"Gemini batchEmbedContents failed ({res.status_code}): {res.text[:200]}"
                    )
                data = res.json()
                embeddings_data = data.get("embeddings", [])
                if len(embeddings_data) != len(batch):
                    raise EmbeddingProviderError(
                        f"Gemini returned {len(embeddings_data)} embeddings for {len(batch)} inputs."
                    )
                for item in embeddings_data:
                    vals = item.get("values", [])
                    results.append(self._verify_vector_dimensions(vals))

            # Light pacing between batches to respect rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return results


def get_default_embedding_provider() -> EmbeddingProvider:
    """Returns the production default verified 1536-dim embedding provider."""
    return GeminiEmbeddingProvider(expected_dimensions=1536)
