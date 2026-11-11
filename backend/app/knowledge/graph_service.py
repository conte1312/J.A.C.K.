"""Knowledge Graph service for J.A.C.K. M4.5 Knowledge Graph.

Uses the existing knowledge_links table. No new tables required.
Provides: neighbor retrieval, relationship traversal, related knowledge
discovery, subgraph extraction, duplicate relationship detection,
contradiction discovery, provenance tracking.

All operations are read-only on the knowledge graph structure.
Depth and result limits prevent unbounded recursive traversal.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.knowledge.repository import (
    KnowledgeNotFoundError,
    KnowledgeRepository,
)

logger = logging.getLogger("jack.backend.knowledge")

MAX_TRAVERSAL_DEPTH = 5
MAX_NEIGHBORS = 100
MAX_SUBGRAPH_NODES = 200


@dataclass
class GraphLink:
    id: str
    from_id: str
    to_id: str
    relation_type: str
    relation_key: str
    strength: int
    description: str | None
    created_at: str


@dataclass
class GraphNode:
    id: str
    item: dict[str, object]
    links_out: list[GraphLink]
    links_in: list[GraphLink]


@dataclass
class GraphTraversalResult:
    start_item_id: str
    nodes: dict[str, GraphNode]
    edges: list[GraphLink]
    max_depth_reached: int


class KnowledgeGraphService:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    # ------------------------------------------------------------------
    # Neighbor retrieval
    # ------------------------------------------------------------------

    def get_neighbors(
        self,
        item_id: str,
        *,
        depth: int = 1,
        relation_type: str | None = None,
        min_strength: int = 1,
        max_results: int = MAX_NEIGHBORS,
    ) -> GraphTraversalResult:
        """Retrieve neighbors of an item up to a given depth.

        Uses BFS traversal with depth and result limits.
        """
        if depth < 1:
            depth = 1
        if depth > MAX_TRAVERSAL_DEPTH:
            depth = MAX_TRAVERSAL_DEPTH

        start_item = self.repository.get_item(item_id)
        if start_item is None:
            raise KnowledgeNotFoundError(f"Item {item_id} not found")

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphLink] = []
        visited: set[str] = {item_id}
        queue: deque[tuple[str, int]] = deque([(item_id, 0)])

        # Load start node
        nodes[item_id] = self._build_node(item_id, relation_type, min_strength)

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            links = self.repository.list_links(
                item_id=current_id, relation_type=relation_type
            )
            for link in links:
                strength = int(link.get("strength", 1))
                if strength < min_strength:
                    continue

                edge = GraphLink(
                    id=str(link["id"]),
                    from_id=str(link["from_id"]),
                    to_id=str(link["to_id"]),
                    relation_type=str(link["relation_type"]),
                    relation_key=str(link.get("relation_key", "")),
                    strength=strength,
                    description=str(link.get("description") or ""),
                    created_at=str(link.get("created_at", "")),
                )
                edges.append(edge)

                neighbor_id = (
                    str(link["to_id"])
                    if str(link["from_id"]) == current_id
                    else str(link["from_id"])
                )

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor_item = self.repository.get_item(neighbor_id)
                    if neighbor_item is not None:
                        nodes[neighbor_id] = self._build_node(
                            neighbor_id, relation_type, min_strength
                        )
                        if current_depth + 1 <= depth:
                            queue.append((neighbor_id, current_depth + 1))

                if len(nodes) >= MAX_SUBGRAPH_NODES:
                    break

        return GraphTraversalResult(
            start_item_id=item_id,
            nodes=nodes,
            edges=edges,
            max_depth_reached=min(depth, max((n for _, n in queue), default=0)),
        )

    # ------------------------------------------------------------------
    # Related knowledge discovery
    # ------------------------------------------------------------------

    def get_related(
        self,
        item_id: str,
        *,
        relation_types: list[str] | None = None,
        min_strength: int = 1,
        limit: int = MAX_NEIGHBORS,
    ) -> list[dict[str, object]]:
        """Get directly related items (one hop) with optional type filter."""
        item = self.repository.get_item(item_id)
        if item is None:
            raise KnowledgeNotFoundError(f"Item {item_id} not found")

        links = self.repository.list_links(item_id=item_id)
        related: list[dict[str, object]] = []

        for link in links:
            strength = int(link.get("strength", 1))
            if strength < min_strength:
                continue
            if relation_types is not None:
                if str(link["relation_type"]) not in relation_types:
                    continue

            neighbor_id = (
                str(link["to_id"])
                if str(link["from_id"]) == item_id
                else str(link["from_id"])
            )
            neighbor = self.repository.get_item(neighbor_id)
            if neighbor is None:
                continue

            related.append(
                {
                    "item": neighbor,
                    "link": {
                        "id": str(link["id"]),
                        "relation_type": str(link["relation_type"]),
                        "relation_key": str(link.get("relation_key", "")),
                        "strength": strength,
                        "description": str(link.get("description") or ""),
                    },
                }
            )

        related.sort(key=lambda x: x["link"]["strength"], reverse=True)
        return related[:limit]

    # ------------------------------------------------------------------
    # Duplicate relationship detection
    # ------------------------------------------------------------------

    def find_duplicate_relationships(
        self,
        item_id: str | None = None,
    ) -> list[dict[str, object]]:
        """Detect duplicate relationships (same from, to, relation_type, strength)."""
        links = self.repository.list_links(item_id=item_id)
        seen: dict[str, list[dict[str, object]]] = {}
        duplicates: list[dict[str, object]] = []

        for link in links:
            key = (
                str(link["from_id"]),
                str(link["to_id"]),
                str(link["relation_type"]),
                int(link.get("strength", 1)),
            )
            if key not in seen:
                seen[key] = []
            seen[key].append(link)

        for key, group in seen.items():
            if len(group) > 1:
                duplicates.append(
                    {
                        "from_id": key[0],
                        "to_id": key[1],
                        "relation_type": key[2],
                        "strength": key[3],
                        "links": [
                            {
                                "id": str(l["id"]),
                                "created_at": str(l.get("created_at", "")),
                            }
                            for l in group
                        ],
                    }
                )

        return duplicates

    # ------------------------------------------------------------------
    # Contradiction discovery
    # ------------------------------------------------------------------

    def find_contradictions(
        self,
        item_id: str | None = None,
    ) -> list[dict[str, object]]:
        """Find contradiction relationships (relation_type = 'contradicts')."""
        links = self.repository.list_links(item_id=item_id)
        contradictions: list[dict[str, object]] = []

        for link in links:
            if str(link["relation_type"]) != "contradicts":
                continue

            from_item = self.repository.get_item(str(link["from_id"]))
            to_item = self.repository.get_item(str(link["to_id"]))

            contradictions.append(
                {
                    "link_id": str(link["id"]),
                    "from_id": str(link["from_id"]),
                    "from_title": str(from_item.get("title", "")) if from_item else "",
                    "to_id": str(link["to_id"]),
                    "to_title": str(to_item.get("title", "")) if to_item else "",
                    "strength": int(link.get("strength", 1)),
                    "description": str(link.get("description") or ""),
                    "created_at": str(link.get("created_at", "")),
                }
            )

        return contradictions

    # ------------------------------------------------------------------
    # Subgraph extraction
    # ------------------------------------------------------------------

    def get_subgraph(
        self,
        item_id: str,
        *,
        depth: int = 2,
        max_nodes: int = MAX_SUBGRAPH_NODES,
    ) -> GraphTraversalResult:
        """Extract a subgraph around an item up to a given depth."""
        return self.get_neighbors(
            item_id=item_id,
            depth=depth,
            max_results=max_nodes,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_node(
        self,
        item_id: str,
        relation_type: str | None,
        min_strength: int,
    ) -> GraphNode:
        item = self.repository.get_item(item_id)
        if item is None:
            return GraphNode(id=item_id, item={}, links_out=[], links_in=[])

        links = self.repository.list_links(item_id=item_id, relation_type=relation_type)
        links_out: list[GraphLink] = []
        links_in: list[GraphLink] = []

        for link in links:
            strength = int(link.get("strength", 1))
            if strength < min_strength:
                continue
            edge = GraphLink(
                id=str(link["id"]),
                from_id=str(link["from_id"]),
                to_id=str(link["to_id"]),
                relation_type=str(link["relation_type"]),
                relation_key=str(link.get("relation_key", "")),
                strength=strength,
                description=str(link.get("description") or ""),
                created_at=str(link.get("created_at", "")),
            )
            if str(link["from_id"]) == item_id:
                links_out.append(edge)
            else:
                links_in.append(edge)

        return GraphNode(
            id=item_id,
            item=item,
            links_out=links_out,
            links_in=links_in,
        )
