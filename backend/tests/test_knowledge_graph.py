"""J.A.C.K. M4.5 Knowledge Graph tests.

Tests for graph traversal, neighbor retrieval, related discovery,
contradiction detection, duplicate detection, and graph API.
Uses isolated temporary databases.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.routes.v2.knowledge import (
    get_graph,
    get_graph_contradictions,
    get_graph_duplicates,
    get_graph_neighbors,
    get_graph_related,
)
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.repository import KnowledgeRepository


def _make_request(repository: KnowledgeRepository) -> MagicMock:
    request = MagicMock()
    request.app.state.knowledge_repository = repository
    return request


class KnowledgeGraphServiceTests(unittest.TestCase):
    """Tests for KnowledgeGraphService (M4.5)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-graph-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = KnowledgeGraphService(repository=self.repository)

        self.domain = self.repository.create_domain(
            name="Graph Domain", slug="graph-domain"
        )
        self.a = self.repository.create_item(
            title="Item A", content="Content A",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        self.b = self.repository.create_item(
            title="Item B", content="Content B",
            domain_id=self.domain["id"],
            knowledge_type="fact",
            source_type="document",
            verification_status="provisional",
            item_state="published",
        )
        self.c = self.repository.create_item(
            title="Item C", content="Content C",
            domain_id=self.domain["id"],
            knowledge_type="procedure",
            source_type="document",
            verification_status="unverified",
            item_state="published",
        )
        self.d = self.repository.create_item(
            title="Item D", content="Content D",
            domain_id=self.domain["id"],
            knowledge_type="reference",
            source_type="document",
            verification_status="inferred",
            item_state="archived",
        )

        # Create links
        self.l_ab = self.repository.create_link(
            from_id=self.a["id"], to_id=self.b["id"],
            relation_type="related", strength=2,
        )
        self.l_bc = self.repository.create_link(
            from_id=self.b["id"], to_id=self.c["id"],
            relation_type="supports", strength=3,
        )
        self.l_cd = self.repository.create_link(
            from_id=self.c["id"], to_id=self.d["id"],
            relation_type="contradicts", strength=1,
        )
        self.l_ba = self.repository.create_link(
            from_id=self.b["id"], to_id=self.a["id"],
            relation_type="related", strength=1,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_get_neighbors_depth_1(self) -> None:
        result = self.service.get_neighbors(
            item_id=self.a["id"], depth=1
        )
        self.assertEqual(result.start_item_id, self.a["id"])
        neighbor_ids = {n.id for n in result.nodes.values() if n.id != self.a["id"]}
        self.assertIn(self.b["id"], neighbor_ids)

    def test_get_neighbors_depth_2(self) -> None:
        result = self.service.get_neighbors(
            item_id=self.a["id"], depth=2
        )
        neighbor_ids = {n.id for n in result.nodes.values() if n.id != self.a["id"]}
        self.assertIn(self.b["id"], neighbor_ids)
        self.assertIn(self.c["id"], neighbor_ids)
        # Depth 2 should not reach D (A->B->C->D is depth 3)
        self.assertNotIn(self.d["id"], neighbor_ids)

    def test_get_neighbors_relation_filter(self) -> None:
        result = self.service.get_neighbors(
            item_id=self.b["id"], depth=1,
            relation_type="supports"
        )
        neighbor_ids = {n.id for n in result.nodes.values() if n.id != self.b["id"]}
        self.assertIn(self.c["id"], neighbor_ids)
        self.assertNotIn(self.a["id"], neighbor_ids)

    def test_get_neighbors_min_strength(self) -> None:
        result = self.service.get_neighbors(
            item_id=self.a["id"], depth=1, min_strength=3
        )
        neighbor_ids = {n.id for n in result.nodes.values() if n.id != self.a["id"]}
        # Link A->B has strength 2, so should not appear with min_strength=3
        self.assertNotIn(self.b["id"], neighbor_ids)

    def test_get_neighbors_nonexistent(self) -> None:
        with self.assertRaises(Exception):
            self.service.get_neighbors(item_id="nonexistent-id")

    def test_get_related(self) -> None:
        related = self.service.get_related(
            item_id=self.b["id"], limit=10
        )
        titles = {r["item"]["title"] for r in related}
        self.assertIn("Item A", titles)
        self.assertIn("Item C", titles)

    def test_get_related_filter_type(self) -> None:
        related = self.service.get_related(
            item_id=self.b["id"],
            relation_types=["supports"],
            limit=10,
        )
        titles = {r["item"]["title"] for r in related}
        self.assertIn("Item C", titles)
        self.assertNotIn("Item A", titles)

    def test_get_related_min_strength(self) -> None:
        related = self.service.get_related(
            item_id=self.b["id"],
            min_strength=3,
            limit=10,
        )
        titles = {r["item"]["title"] for r in related}
        # B->C has strength 3, B->A has strength 2
        self.assertIn("Item C", titles)
        self.assertNotIn("Item A", titles)

    def test_get_related_nonexistent(self) -> None:
        with self.assertRaises(Exception):
            self.service.get_related(item_id="nonexistent-id")

    def test_find_contradictions(self) -> None:
        contradictions = self.service.find_contradictions(
            item_id=self.c["id"]
        )
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["from_id"], self.c["id"])
        self.assertEqual(contradictions[0]["to_id"], self.d["id"])

    def test_find_contradictions_none(self) -> None:
        contradictions = self.service.find_contradictions(
            item_id=self.a["id"]
        )
        self.assertEqual(len(contradictions), 0)

    def test_find_duplicate_relationships(self) -> None:
        # A->B and B->A are not duplicates (different direction)
        dupes = self.service.find_duplicate_relationships(
            item_id=self.a["id"]
        )
        # No true duplicates in our setup
        self.assertEqual(len(dupes), 0)

    def test_get_subgraph(self) -> None:
        result = self.service.get_subgraph(
            item_id=self.a["id"], depth=2
        )
        self.assertEqual(result.start_item_id, self.a["id"])
        self.assertGreaterEqual(len(result.nodes), 2)


# ---- API Tests ----

class GraphApiTests(unittest.TestCase):
    """Tests for M4.5 Graph API routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-graph-api-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = KnowledgeGraphService(repository=self.repository)
        self.request = _make_request(self.repository)

        self.domain = self.repository.create_domain(
            name="Graph API Domain", slug="graph-api-domain"
        )
        self.a = self.repository.create_item(
            title="Graph Item A", content="Content A",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        self.b = self.repository.create_item(
            title="Graph Item B", content="Content B",
            domain_id=self.domain["id"],
            knowledge_type="fact",
            source_type="document",
            verification_status="provisional",
            item_state="published",
        )
        self.repository.create_link(
            from_id=self.a["id"], to_id=self.b["id"],
            relation_type="related", strength=2,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_api_get_graph(self) -> None:
        result = get_graph(item_id=self.a["id"], depth=2, service=self.service)
        self.assertEqual(result["start_item_id"], self.a["id"])
        self.assertGreaterEqual(len(result["nodes"]), 1)

    def test_api_get_graph_nonexistent(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_graph(item_id="nonexistent-id", depth=1, service=self.service)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_get_graph_neighbors(self) -> None:
        result = get_graph_neighbors(
            item_id=self.a["id"], depth=1, service=self.service
        )
        self.assertEqual(result["start_item_id"], self.a["id"])
        neighbor_ids = {n["id"] for n in result["nodes"] if n["id"] != self.a["id"]}
        self.assertIn(self.b["id"], neighbor_ids)

    def test_api_get_graph_related(self) -> None:
        result = get_graph_related(
            item_id=self.b["id"], service=self.service
        )
        self.assertGreaterEqual(len(result), 1)
        titles = {r["title"] for r in result}
        self.assertIn("Graph Item A", titles)

    def test_api_get_graph_related_filter(self) -> None:
        result = get_graph_related(
            item_id=self.b["id"],
            relation_type="related",
            service=self.service,
        )
        titles = {r["title"] for r in result}
        self.assertIn("Graph Item A", titles)

    def test_api_get_graph_contradictions(self) -> None:
        # No contradictions in our setup
        result = get_graph_contradictions(
            item_id=self.a["id"], service=self.service
        )
        self.assertEqual(len(result), 0)

    def test_api_get_graph_duplicates(self) -> None:
        # No duplicates in our setup
        result = get_graph_duplicates(
            item_id=self.a["id"], service=self.service
        )
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
