"""Context Builder for J.A.C.K. M4.6 Context Builder.

Builds structured context packages for the Conversation Engine and AI
orchestrator. All operations are read-only.

Features:
- Token-aware context construction with budget limits
- Source preservation for every retrieved fact
- Verification status indicators (never merge provisional with verified)
- Uncertainty preservation when evidence is insufficient
- Optional M3 personal context via read-only interface
- Duplicate removal
- Configurable context budget per target model
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.knowledge.context_resolver import (
    ContextualResolver,
    ResolutionPlan,
    ResolvedContext,
)
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.m3_interface import MemoryReadInterface
from app.knowledge.repository import KnowledgeRepository

logger = logging.getLogger("jack.backend.knowledge")

# Default token budget per model family (conservative estimates)
DEFAULT_TOKEN_BUDGET = 4000
RESERVED_FOR_QUERY = 500
RESERVED_FOR_RESPONSE = 1000


@dataclass
class ContextItem:
    """Single knowledge item in context package."""

    item_id: str
    title: str
    content: str
    source_type: str
    source_id: str | None
    domain_id: str
    verification_status: str
    item_state: str
    confidence: float  # 0.0-1.0 derived from verification_status
    is_personal: bool = False
    source_provenance: dict[str, object] | None = None
    tokens_estimated: int = 0


@dataclass
class ContextPackage:
    """Structured context package for AI consumption."""

    query: str
    items: list[ContextItem]
    total_items: int
    total_tokens_estimated: int
    token_budget: int
    verification_summary: dict[str, int]
    sources: list[dict[str, object]]
    graph_links: list[dict[str, object]]
    uncertainty_notes: list[str]
    generated_at: str
    context_version: str = "1.0"


class ContextBuilder:
    """Builds structured context packages from resolved knowledge."""

    # Verification status -> confidence score mapping
    VERIFICATION_CONFIDENCE = {
        "verified": 0.95,
        "provisional": 0.60,
        "inferred": 0.40,
        "unverified": 0.20,
        "contradicted": 0.10,
    }

    # Rough token estimate: 1 token ≈ 0.75 words for English
    CHARS_PER_TOKEN = 4.0

    def __init__(
        self,
        repository: KnowledgeRepository,
        graph_service: KnowledgeGraphService | None = None,
        m3_memory: MemoryReadInterface | None = None,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> None:
        self.repository = repository
        self.graph_service = graph_service
        self.m3_memory = m3_memory
        self.token_budget = token_budget
        self.resolver = ContextualResolver(
            repository=repository,
            graph_service=graph_service,
        )

    def build_context(
        self,
        query: str,
        *,
        conversation_context: str | None = None,
        domain_id: str | None = None,
        max_items: int = 10,
        target_model_context: int | None = None,
        include_personal: bool = False,
    ) -> ContextPackage:
        """Build a structured context package for a query.

        Args:
            query: User query string.
            conversation_context: Optional conversation history text.
            domain_id: Optional domain filter.
            max_items: Maximum number of knowledge items.
            target_model_context: Target model context window (tokens).
            include_personal: Whether to include M3 personal context.
        """
        # Determine effective token budget
        budget = self._compute_budget(target_model_context)

        # Resolve query to plan
        plan = self.resolver.resolve(
            query=query,
            conversation_context=conversation_context,
            domain_id=domain_id,
            max_items=max_items,
            max_chunks=max_items * 2,
        )

        # Build resolved context
        resolved = self.resolver.build_context(plan)

        # Convert to context items with token estimation
        context_items: list[ContextItem] = []
        used_tokens = 0
        uncertainty_notes: list[str] = []

        for item in resolved.items:
            item_tokens = self._estimate_tokens(
                str(item.get("title", "")) + " " + str(item.get("content", ""))
            )
            if used_tokens + item_tokens > budget:
                uncertainty_notes.append(
                    f"Context budget exhausted; {len(resolved.items) - len(context_items)} "
                    "additional items omitted"
                )
                break

            vs = str(item.get("verification_status", "unverified"))
            confidence = self.VERIFICATION_CONFIDENCE.get(vs, 0.2)

            # Add uncertainty note for low-confidence items
            if vs in ("unverified", "contradicted"):
                uncertainty_notes.append(
                    f"Item '{str(item.get('title', ''))[:50]}' has "
                    f"verification status '{vs}'; treat as uncertain"
                )

            context_items.append(
                ContextItem(
                    item_id=str(item["id"]),
                    title=str(item.get("title", "")),
                    content=str(item.get("content", "")),
                    source_type=str(item.get("source_type", "")),
                    source_id=str(item.get("source_id") or ""),
                    domain_id=str(item.get("domain_id", "")),
                    verification_status=vs,
                    item_state=str(item.get("item_state", "")),
                    confidence=confidence,
                    is_personal=False,
                    source_provenance={
                        "source_id": str(item.get("source_id") or ""),
                        "source_type": str(item.get("source_type", "")),
                        "domain_id": str(item.get("domain_id", "")),
                    },
                    tokens_estimated=item_tokens,
                )
            )
            used_tokens += item_tokens

        # Optional M3 personal context (read-only)
        personal_items: list[ContextItem] = []
        if include_personal and self.m3_memory is not None:
            personal_items = self._build_personal_context(
                query=query,
                remaining_budget=budget - used_tokens,
            )
            used_tokens += sum(it.tokens_estimated for it in personal_items)

        # Verification summary
        verification_summary: dict[str, int] = {}
        for item in context_items:
            vs = item.verification_status
            verification_summary[vs] = verification_summary.get(vs, 0) + 1

        # Sources
        sources: list[dict[str, object]] = []
        seen_sources: set[str] = set()
        for item in context_items:
            sid = item.source_id
            if sid and sid not in seen_sources:
                seen_sources.add(sid)
                sources.append(
                    {
                        "source_id": sid,
                        "source_type": item.source_type,
                        "domain_id": item.domain_id,
                        "verification_status": item.verification_status,
                    }
                )

        # Graph links (from resolved context)
        graph_links = resolved.graph_links

        return ContextPackage(
            query=query,
            items=context_items + personal_items,
            total_items=len(context_items) + len(personal_items),
            total_tokens_estimated=used_tokens,
            token_budget=budget,
            verification_summary=verification_summary,
            sources=sources,
            graph_links=graph_links,
            uncertainty_notes=uncertainty_notes,
            generated_at=datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
        )

    # ------------------------------------------------------------------
    # Personal context (M3 read-only)
    # ------------------------------------------------------------------

    def _build_personal_context(
        self,
        query: str,
        remaining_budget: int,
    ) -> list[ContextItem]:
        """Build personal context from M3 via read-only interface."""
        if self.m3_memory is None or remaining_budget <= 0:
            return []

        try:
            items = self.m3_memory.search_items(
                query=query,
                limit=5,
            )
        except Exception:
            logger.exception("Failed to retrieve personal context from M3")
            return []

        personal: list[ContextItem] = []
        used = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", ""))
            title = str(item.get("title", ""))
            tokens = self._estimate_tokens(title + " " + content)
            if used + tokens > remaining_budget:
                break
            personal.append(
                ContextItem(
                    item_id=str(item.get("id", "")),
                    title=title,
                    content=content,
                    source_type=str(item.get("source_type", "saved")),
                    source_id=str(item.get("id", "")),
                    domain_id=str(item.get("category", "personal")),
                    verification_status=str(item.get("verification", "to_verify")),
                    item_state=str(item.get("item_state", "published")),
                    confidence=self.VERIFICATION_CONFIDENCE.get(
                        str(item.get("verification", "to_verify")), 0.5
                    ),
                    is_personal=True,
                    source_provenance={
                        "source": "M3 personal memory",
                        "category": str(item.get("category", "")),
                    },
                    tokens_estimated=tokens,
                )
            )
            used += tokens

        return personal

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_budget(
        self,
        target_model_context: int | None,
    ) -> int:
        """Compute effective token budget for context."""
        if target_model_context is not None:
            # Reserve tokens for query and response
            available = target_model_context - RESERVED_FOR_QUERY - RESERVED_FOR_RESPONSE
            return max(500, min(available, self.token_budget))
        return self.token_budget

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: chars / 4."""
        if not text:
            return 0
        return max(1, int(len(text) / self.CHARS_PER_TOKEN))
