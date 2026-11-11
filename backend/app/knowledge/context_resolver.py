"""Contextual Resolver for J.A.C.K. M4.6 Context Builder.

Analyzes user query, conversation context, relevant domains,
knowledge items, documents, graph relationships, and verification
status to determine what knowledge is needed.

All operations are read-only. No writes to M3 or M4 repositories.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.knowledge.repository import KnowledgeRepository
from app.knowledge.graph_service import KnowledgeGraphService

logger = logging.getLogger("jack.backend.knowledge")


@dataclass
class ResolutionPlan:
    """Plan describing what knowledge should be retrieved for a query."""

    query: str
    key_terms: list[str]
    relevant_domains: list[str]
    relevant_item_types: list[str]
    suggested_verification: list[str]
    include_graph: bool
    max_items: int
    max_chunks: int
    reason: str


@dataclass
class ResolvedContext:
    """Resolved knowledge context for a query."""

    query: str
    items: list[dict[str, object]]
    document_chunks: list[dict[str, object]]
    graph_links: list[dict[str, object]]
    verification_summary: dict[str, int]
    sources: list[dict[str, object]]
    resolved_at: str


class ContextualResolver:
    """Analyzes queries and builds resolution plans."""

    # Domain keywords for heuristic domain detection
    DOMAIN_KEYWORDS = {
        "work": ["meeting", "project", "deadline", "client", "report", "task"],
        "technical": ["code", "api", "server", "database", "algorithm",
                      "technical", "engineering", "software"],
        "people": ["person", "contact", "colleague", "manager", "team"],
        "projects": ["project", "milestone", "deliverable", "roadmap"],
        "preferences": ["prefer", "like", "dislike", "setting", "config"],
        "events": ["event", "conference", "workshop", "seminar", "webinar"],
        "identity": ["identity", "profile", "account", "user", "personal"],
    }

    def __init__(
        self,
        repository: KnowledgeRepository,
        graph_service: KnowledgeGraphService | None = None,
    ) -> None:
        self.repository = repository
        self.graph_service = graph_service

    def resolve(
        self,
        query: str,
        *,
        conversation_context: str | None = None,
        domain_id: str | None = None,
        max_items: int = 10,
        max_chunks: int = 20,
    ) -> ResolutionPlan:
        """Analyze query and context to produce a resolution plan."""
        if not query or not query.strip():
            return ResolutionPlan(
                query=query,
                key_terms=[],
                relevant_domains=[],
                relevant_item_types=[],
                suggested_verification=["verified", "provisional"],
                include_graph=False,
                max_items=max_items,
                max_chunks=max_chunks,
                reason="Empty query",
            )

        key_terms = self._extract_key_terms(query)
        relevant_domains = self._detect_domains(query, key_terms)
        relevant_item_types = self._detect_item_types(query, key_terms)
        include_graph = self._should_include_graph(query, key_terms)

        # Combine explicit domain filter with detected ones
        if domain_id:
            domains = [domain_id]
        else:
            domains = relevant_domains

        reason = (
            f"Query contains {len(key_terms)} key terms; "
            f"detected {len(domains)} relevant domain(s); "
            f"graph traversal {'enabled' if include_graph else 'disabled'}"
        )

        return ResolutionPlan(
            query=query,
            key_terms=key_terms,
            relevant_domains=domains,
            relevant_item_types=relevant_item_types,
            suggested_verification=["verified", "provisional"],
            include_graph=include_graph,
            max_items=max_items,
            max_chunks=max_chunks,
            reason=reason,
        )

    def build_context(
        self,
        plan: ResolutionPlan,
    ) -> ResolvedContext:
        """Execute the resolution plan and build a resolved context."""
        items: list[dict[str, object]] = []
        document_chunks: list[dict[str, object]] = []
        graph_links: list[dict[str, object]] = []
        sources: list[dict[str, object]] = []

        # Search items
        search_domains = plan.relevant_domains or [None]
        for domain in search_domains:
            results = self.repository.search_items(
                query=plan.query,
                domain_id=domain,
                knowledge_type=(
                    plan.relevant_item_types[0]
                    if plan.relevant_item_types
                    else None
                ),
                verification_status=None,
                item_state="published",
                limit=plan.max_items // max(len(search_domains), 1),
            )
            for item in results:
                if item not in items:
                    items.append(item)
                    sources.append(
                        {
                            "source_id": str(item.get("source_id", "")),
                            "source_type": str(item.get("source_type", "")),
                            "title": str(item.get("title", "")),
                            "verification_status": str(
                                item.get("verification_status", "")
                            ),
                            "domain_id": str(item.get("domain_id", "")),
                        }
                    )

        # Graph traversal for top items
        if plan.include_graph and self.graph_service is not None and items:
            top_item = items[0]
            top_id = str(top_item["id"])
            try:
                traversal = self.graph_service.get_neighbors(
                    item_id=top_id,
                    depth=1,
                    min_strength=1,
                    max_results=plan.max_chunks,
                )
                for link in traversal.edges:
                    graph_links.append(
                        {
                            "id": e.id if hasattr(e, "id") else str(e.get("id", "")),
                            "from_id": e.from_id if hasattr(e, "from_id") else str(e.get("from_id", "")),
                            "to_id": e.to_id if hasattr(e, "to_id") else str(e.get("to_id", "")),
                            "relation_type": e.relation_type if hasattr(e, "relation_type") else str(e.get("relation_type", "")),
                            "strength": e.strength if hasattr(e, "strength") else int(e.get("strength", 1)),
                        }
                        for e in [link]
                    )
            except Exception:
                logger.exception("Graph traversal failed for item %s", top_id)

        # Verification summary
        verification_summary: dict[str, int] = {}
        for item in items:
            vs = str(item.get("verification_status", "unknown"))
            verification_summary[vs] = verification_summary.get(vs, 0) + 1

        return ResolvedContext(
            query=plan.query,
            items=items[: plan.max_items],
            document_chunks=document_chunks,
            graph_links=graph_links,
            verification_summary=verification_summary,
            sources=sources,
            resolved_at=datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_key_terms(self, query: str) -> list[str]:
        """Extract meaningful terms from query."""
        # Remove punctuation, split, filter short words
        cleaned = re.sub(r"[^\w\s]", " ", query.lower())
        terms = [t for t in cleaned.split() if len(t) >= 3]
        # Deduplicate preserving order
        seen: set[str] = set()
        result: list[str] = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result[:10]

    def _detect_domains(
        self,
        query: str,
        key_terms: list[str],
    ) -> list[str]:
        """Detect relevant domains from query terms."""
        query_lower = query.lower()
        detected: list[str] = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(k in query_lower for k in keywords):
                detected.append(domain)
        return detected

    def _detect_item_types(
        self,
        query: str,
        key_terms: list[str],
    ) -> list[str]:
        """Detect relevant item types from query."""
        query_lower = query.lower()
        types: list[str] = []
        if any(k in query_lower for k in ["how", "tutorial", "guide", "procedure"]):
            types.append("procedure")
        if any(k in query_lower for k in ["fact", "definition", "what is"]):
            types.append("definition")
        if any(k in query_lower for k in ["formula", "equation", "theorem"]):
            types.append("formula")
        if not types:
            types.append("concept")
        return types

    def _should_include_graph(
        self,
        query: str,
        key_terms: list[str],
    ) -> bool:
        """Determine if graph traversal should be included."""
        query_lower = query.lower()
        graph_triggers = ["related", "connected", "link", "relationship",
                          "depends", "part of", "causes", "influences"]
        return any(k in query_lower for k in graph_triggers)
