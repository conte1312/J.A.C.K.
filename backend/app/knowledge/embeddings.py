"""Embedding provider abstraction for J.A.C.K. M4.4 Semantic Retrieval.

Provider-independent interface for generating embeddings.
Prefers local/free options; never requires a paid API.
Never downloads large models automatically without resource checks.
"""

from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("jack.backend.knowledge")


@dataclass
class EmbeddingResult:
    vector: list[float]
    model: str
    model_version: str
    dimensions: int


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...

    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingResult:
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        ...


class LocalEmbeddingProvider(EmbeddingProvider):
    """Lightweight local embedding provider.

    Uses a deterministic hash-based projection. Not semantically rich like
    a real transformer, but provides a working semantic retrieval path
    without downloading any model. Graceful fallback when no AI provider
    supports embeddings.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return "local-hash"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_text(self, text: str) -> EmbeddingResult:
        vector = self._hash_vector(text)
        return EmbeddingResult(
            vector=vector,
            model=self.model_name,
            model_version=self.model_version,
            dimensions=self._dimensions,
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return [self.embed_text(t) for t in texts]

    def _hash_vector(self, text: str) -> list[float]:
        """Deterministic projection of text into a fixed-dimensional vector.

        Uses multiple SHA-256 hashes of text + salt to populate dimensions.
        Values are in [-1, 1]. Same text always yields same vector.
        """
        vector = [0.0] * self._dimensions
        if not text:
            return vector
        text = text.strip().lower()
        for i in range(self._dimensions):
            salt = f"{i}:{text}"
            h = hashlib.sha256(salt.encode("utf-8")).hexdigest()
            # Map hex digest to [-1, 1]
            val = int(h[:8], 16) / 0xFFFFFFFF
            vector[i] = (val * 2) - 1
        return vector


def cosine_similarity(a: list[float] | EmbeddingResult, b: list[float] | EmbeddingResult) -> float:
    """Cosine similarity between two vectors or EmbeddingResult objects."""
    a_vec = a.vector if isinstance(a, EmbeddingResult) else a
    b_vec = b.vector if isinstance(b, EmbeddingResult) else b
    if len(a_vec) != len(b_vec):
        raise ValueError("Vector dimensions must match")
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a_vec, b_vec):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


# Optional real semantic embedding provider.
# Requires: pip install sentence-transformers (which brings torch).
# Not installed by default to keep the default dependency set lightweight.
class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider.

    Uses a small local model (default: all-MiniLM-L6-v2, ~80 MB) to produce
    real semantic embeddings. Falls back gracefully if sentence-transformers
    is not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._dimensions: int | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self._model_name)
            # Determine embedding dimension by encoding a probe string.
            probe = self._model.encode(["probe"], convert_to_numpy=True)
            self._dimensions = int(probe.shape[1])
        except ImportError as error:
            raise ImportError(
                "sentence-transformers non è installato. "
                "Installa con: pip install sentence-transformers"
            ) from error

    @property
    def model_name(self) -> str:
        return f"sentence-transformers:{self._model_name}"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    @property
    def dimensions(self) -> int:
        self._ensure_loaded()
        if self._dimensions is None:
            raise RuntimeError("Embedding model not loaded.")
        return self._dimensions

    def embed_text(self, text: str) -> EmbeddingResult:
        self._ensure_loaded()
        assert self._model is not None
        vector = self._model.encode([text], convert_to_numpy=True)[0]
        return EmbeddingResult(
            vector=[float(v) for v in vector],
            model=self.model_name,
            model_version=self.model_version,
            dimensions=self.dimensions,
        )

    def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        self._ensure_loaded()
        assert self._model is not None
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return [
            EmbeddingResult(
                vector=[float(v) for v in vec],
                model=self.model_name,
                model_version=self.model_version,
                dimensions=self.dimensions,
            )
            for vec in vectors
        ]
