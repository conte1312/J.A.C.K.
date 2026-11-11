"""Hybrid search engine for J.A.C.K. M4.4 Semantic Retrieval.

Combines existing FTS5 full-text search with semantic similarity,
metadata filters, domain relevance, verification status, and recency.
Does not remove or replace FTS5.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from app.knowledge.chunking import DocumentChunker  # noqa: F401  (placeholder)
from app.knowledge.embeddings import EmbeddingProvider, cosine_similarity
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.vector_store import VectorStore

logger = logging.getLogger("jack.backend.knowledge")


@dataclass
class SearchResult:
    item: dict[str, object]
    score: float
    ft_score: float | None
    semantic_score: float | None
    match_reasons: list[str]


class HybridSearchEngine:
    def __init__(
        self,
        repository: KnowledgeRepository,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.repository = repository
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    # Weights for hybrid ranking (configurable)
    WEIGHT_SEMANTIC = 0.5
    WEIGHT_FTS = 0.3
    WEIGHT_RECENCY = 0.1
    WEIGHT_VERIFICATION = 0.1

    VERIFICATION_SCORES = {
        "verified": 1.0,
        "provisional": 0.7,
        "inferred": 0.5,
        "unverified": 0.3,
        "contradicted": 0.1,
    }

    def search(
        self,
        query: str,
        *,
        domain_id: str | None = None,
        knowledge_type: str | None = None,
        verification_status: str | None = None,
        item_state: str | None = "published",
        limit: int = 10,
        offset: int = 0,
        min_similarity: float = 0.1,
    ) -> list[SearchResult]:
        """Hybrid search: FTS5 + semantic + metadata filtering + ranking."""
        if not query or not query.strip():
            return []

        # 1. FTS5 retrieval (existing repository search)
        ft_results = self.repository.search_items(
            query=query,
            domain_id=domain_id,
            knowledge_type=knowledge_type,
            verification_status=verification_status,
            item_state=item_state,
            limit=limit * 3,  # over-fetch for ranking
        )

        # 2. Semantic retrieval
        query_embedding = self.embedding_provider.embed_text(query)
        semantic_results = self.vector_store.search_similar(
            query_vector=query_embedding.vector,
            model_name=query_embedding.model,
            model_version=query_embedding.model_version,
            limit=limit * 3,
            min_similarity=min_similarity,
        )
        semantic_by_item = {item_id: sim for item_id, sim in semantic_results}

        # 3. Build unified candidate set
        candidate_ids: dict[str, dict[str, object]] = {}
        for item in ft_results:
            if self._matches_filters(
                item, domain_id, knowledge_type,
                verification_status, item_state
            ):
                candidate_ids[str(item["id"])] = item

        # Also fetch items for semantic-only results
        for item_id, _ in semantic_results:
            if item_id not in candidate_ids:
                item = self.repository.get_item(item_id)
                if item is not None:
                    # Apply metadata filters
                    if not self._matches_filters(
                        item, domain_id, knowledge_type,
                        verification_status, item_state
                    ):
                        continue
                    candidate_ids[item_id] = item

        # 4. Score and rank
        results: list[SearchResult] = []
        now = self._now_timestamp()
        for item_id, item in candidate_ids.items():
            ft_score = self._compute_ft_score(item, query)
            semantic_score = semantic_by_item.get(item_id, 0.0)
            verification_score = self.VERIFICATION_SCORES.get(
                str(item.get("verification_status", "unverified")), 0.3
            )
            recency_score = self._compute_recency_score(
                item.get("updated_at", ""), now
            )

            hybrid = (
                self.WEIGHT_SEMANTIC * semantic_score
                + self.WEIGHT_FTS * ft_score
                + self.WEIGHT_RECENCY * recency_score
                + self.WEIGHT_VERIFICATION * verification_score
            )

            match_reasons: list[str] = []
            if ft_score > 0:
                match_reasons.append("fts5")
            if semantic_score > 0:
                match_reasons.append("semantic")

            results.append(
                SearchResult(
                    item=item,
                    score=round(hybrid, 4),
                    ft_score=round(ft_score, 4),
                    semantic_score=round(semantic_score, 4),
                    match_reasons=match_reasons,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[offset : offset + limit]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _matches_filters(
        self,
        item: dict[str, object],
        domain_id: str | None,
        knowledge_type: str | None,
        verification_status: str | None,
        item_state: str | None,
    ) -> bool:
        if domain_id is not None and str(item.get("domain_id", "")) != domain_id:
            return False
        if knowledge_type is not None and str(item.get("knowledge_type", "")) != knowledge_type:
            return False
        if verification_status is not None and str(item.get("verification_status", "")) != verification_status:
            return False
        if item_state is not None and str(item.get("item_state", "")) != item_state:
            return False
        return True

    def _compute_ft_score(self, item: dict[str, object], query: str) -> float:
        """Simple term-overlap score for FTS results."""
        query_terms = set(query.lower().split())
        text = (
            f"{item.get('title', '')} {item.get('content', '')}"
        ).lower()
        if not query_terms:
            return 0.0
        matches = sum(1 for t in query_terms if t in text)
        return matches / len(query_terms)

    def _compute_recency_score(self, updated_at: str | None, now: str) -> float:
        if not updated_at:
            return 0.0
        try:
            from datetime import datetime

            t = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            n = datetime.fromisoformat(now.replace("Z", "+00:00"))
            days = (n - t).total_seconds() / 86400
            return max(0.0, 1.0 - (days / 365.0))
        except Exception:
            return 0.0

    def _now_timestamp(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )

    def get_search_status(self) -> dict[str, object]:
        return {
            "embedding_provider": self.embedding_provider.model_name,
            "embedding_version": self.embedding_provider.model_version,
            "embedding_dimensions": self.embedding_provider.dimensions,
            "stored_embeddings": self.vector_store.count_embeddings(),
            "fts5_available": True,
        }
