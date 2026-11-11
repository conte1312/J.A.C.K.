"""J.A.C.K. M4.4 Semantic Retrieval tests.

Tests for embedding provider, vector store, hybrid search, and document
import with embeddings. Uses isolated temporary databases.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.routes.v2.knowledge import (
    hybrid_search,
    search_status,
    semantic_search,
)
from app.api.schemas.knowledge import HybridSearchRequest
from app.knowledge.embeddings import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
    cosine_similarity,
)
from app.knowledge.hybrid_search import HybridSearchEngine
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.vector_store import VectorStore


class EmbeddingProviderTests(unittest.TestCase):
    """Tests for LocalEmbeddingProvider (M4.4)."""

    def setUp(self) -> None:
        self.provider = LocalEmbeddingProvider(dimensions=128)

    def test_embedding_deterministic(self) -> None:
        r1 = self.provider.embed_text("Hello world")
        r2 = self.provider.embed_text("Hello world")
        self.assertEqual(r1.vector, r2.vector)
        self.assertEqual(r1.model, "local-hash")
        self.assertEqual(r1.dimensions, 128)

    def test_embedding_different_text_different_vector(self) -> None:
        r1 = self.provider.embed_text("Hello world")
        r2 = self.provider.embed_text("Goodbye world")
        self.assertNotEqual(r1.vector, r2.vector)

    def test_embedding_dimensions(self) -> None:
        self.assertEqual(self.provider.dimensions, 128)
        result = self.provider.embed_text("test")
        self.assertEqual(len(result.vector), 128)

    def test_embedding_batch(self) -> None:
        results = self.provider.embed_batch(["a", "b", "c"])
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertEqual(len(r.vector), 128)

    def test_cosine_similarity(self) -> None:
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)
        self.assertGreater(cosine_similarity(v1, v1), 0.99)

    def test_cosine_similarity_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_cosine_similarity_embedding_result(self) -> None:
        from app.knowledge.embeddings import EmbeddingResult
        v1 = EmbeddingResult(vector=[1.0, 0.0], model="test", model_version="1.0", dimensions=2)
        v2 = EmbeddingResult(vector=[1.0, 0.0], model="test", model_version="1.0", dimensions=2)
        v3 = EmbeddingResult(vector=[0.0, 1.0], model="test", model_version="1.0", dimensions=2)
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)
        self.assertAlmostEqual(cosine_similarity(v1, v1), 1.0)

    def test_cosine_similarity_mixed_list_and_embedding_result(self) -> None:
        from app.knowledge.embeddings import EmbeddingResult
        v1 = [1.0, 0.0]
        v2 = EmbeddingResult(vector=[1.0, 0.0], model="test", model_version="1.0", dimensions=2)
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)

    def test_sentence_transformer_provider_not_installed(self) -> None:
        from app.knowledge.embeddings import SentenceTransformerEmbeddingProvider
        with self.assertRaises(ImportError):
            SentenceTransformerEmbeddingProvider()._ensure_loaded()


class VectorStoreTests(unittest.TestCase):
    """Tests for SQLite vector store (M4.4)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-vs-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        # VectorStore shares the same database as knowledge (FK safety)
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.domain = self.repository.create_domain(
            name="VS Domain", slug="vs-domain"
        )
        self.item = self.repository.create_item(
            title="VS Item",
            content="Vector store test item.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
        )
        self.store = VectorStore(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_store_and_get_embedding(self) -> None:
        eid = self.store.store_embedding(
            item_id=self.item["id"],
            vector=[0.5, 0.5, 0.0],
            model_name="test-model",
            model_version="1.0",
            chunk_id="chunk-1",
        )
        record = self.store.get_embedding(eid)
        self.assertIsNotNone(record)
        self.assertEqual(record.item_id, self.item["id"])
        self.assertEqual(record.chunk_id, "chunk-1")
        self.assertAlmostEqual(record.vector[0], 0.5)

    def test_get_nonexistent_embedding(self) -> None:
        self.assertIsNone(self.store.get_embedding("nonexistent"))

    def test_list_embeddings_for_item(self) -> None:
        self.store.store_embedding(self.item["id"], [0.1, 0.2], "m", "v", chunk_id="c1")
        self.store.store_embedding(self.item["id"], [0.3, 0.4], "m", "v", chunk_id="c2")
        recs = self.store.list_embeddings_for_item(self.item["id"])
        self.assertEqual(len(recs), 2)

    def test_delete_embeddings_for_item(self) -> None:
        self.store.store_embedding(self.item["id"], [0.1, 0.2], "m", "v")
        self.store.store_embedding(self.item["id"], [0.3, 0.4], "m", "v")
        deleted = self.store.delete_embeddings_for_item(self.item["id"])
        self.assertEqual(deleted, 2)
        remaining = self.store.list_embeddings_for_item(self.item["id"])
        self.assertEqual(len(remaining), 0)

    def test_search_similar(self) -> None:
        self.store.store_embedding(self.item["id"], [1.0, 0.0], "local-hash", "1.0.0")
        self.store.store_embedding(self.item["id"], [0.0, 1.0], "local-hash", "1.0.0")
        results = self.store.search_similar(
            query_vector=[1.0, 0.0],
            model_name="local-hash",
            model_version="1.0.0",
            limit=5,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], self.item["id"])
        self.assertGreater(results[0][1], results[1][1])

    def test_count_embeddings(self) -> None:
        self.assertEqual(self.store.count_embeddings(), 0)
        self.store.store_embedding(self.item["id"], [0.1, 0.2], "m", "v")
        self.assertEqual(self.store.count_embeddings(), 1)


class HybridSearchEngineTests(unittest.TestCase):
    """Tests for HybridSearchEngine (M4.4)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-hs-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.vector_store = VectorStore(self.database_path)
        self.provider = LocalEmbeddingProvider(dimensions=64)
        self.engine = HybridSearchEngine(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_provider=self.provider,
        )
        self.domain = self.repository.create_domain(
            name="Test Domain", slug="test-domain"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_item(
        self,
        title: str,
        content: str,
        verification_status: str = "verified",
        item_state: str = "published",
    ) -> dict:
        return self.repository.create_item(
            title=title,
            content=content,
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status=verification_status,
            item_state=item_state,
            tags=[],
            importance=3,
        )

    def test_hybrid_search_empty_query(self) -> None:
        results = self.engine.search(query="")
        self.assertEqual(results, [])

    def test_hybrid_search_fts_only(self) -> None:
        self._create_item("Alpha Project", "Project Alpha meeting notes.")
        self._create_item("Grocery List", "Milk, eggs, bread.")
        results = self.engine.search(query="Alpha", limit=10)
        self.assertGreaterEqual(len(results), 1)
        found = [r.item["title"] for r in results]
        self.assertIn("Alpha Project", found)

    def test_hybrid_search_filter_domain(self) -> None:
        self._create_item("Domain Item", "Content in test domain.")
        other_domain = self.repository.create_domain(
            name="Other", slug="other"
        )
        self.repository.create_item(
            title="Other Domain Item",
            content="Content in other domain.",
            domain_id=other_domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        results = self.engine.search(
            query="Content", domain_id=self.domain["id"], limit=10
        )
        for r in results:
            self.assertEqual(r.item["domain_id"], self.domain["id"])

    def test_hybrid_search_filter_verification(self) -> None:
        self._create_item("Verified Item", "Verified content.", verification_status="verified")
        self._create_item(
            "Unverified Item", "Unverified content.",
            verification_status="unverified",
        )
        results = self.engine.search(
            query="content", verification_status="verified", limit=10
        )
        titles = [r.item["title"] for r in results]
        self.assertIn("Verified Item", titles)
        self.assertNotIn("Unverified Item", titles)

    def test_hybrid_search_ranking(self) -> None:
        self._create_item(
            "Exact Match", "Python programming language tutorial."
        )
        self._create_item(
            "Unrelated", "Gardening tips for beginners."
        )
        results = self.engine.search(query="Python programming", limit=10)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].item["title"], "Exact Match")

    def test_search_status(self) -> None:
        status = self.engine.get_search_status()
        self.assertEqual(status["embedding_provider"], "local-hash")
        self.assertEqual(status["embedding_dimensions"], 64)
        self.assertTrue(status["fts5_available"])

    def test_hybrid_search_no_embeddings(self) -> None:
        # Search without any embeddings stored should still work via FTS5
        self._create_item("FTS Only Item", "Unique searchable term xyzzy.")
        results = self.engine.search(query="xyzzy", limit=10)
        self.assertGreaterEqual(len(results), 1)


class DocumentServiceEmbeddingTests(unittest.TestCase):
    """Tests for document import with embeddings (M4.4)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-doc-emb-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.vector_store = VectorStore(self.database_path)
        self.provider = LocalEmbeddingProvider(dimensions=64)
        self.service = __import__("app.knowledge.document_service", fromlist=["DocumentService"]).DocumentService(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_provider=self.provider,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_import_creates_embedding(self) -> None:
        f = Path(self.temp_dir.name) / "emb_test.txt"
        f.write_text("Embedding test document content.", encoding="utf-8")
        result = self.service.import_document(f)
        self.assertEqual(result.status, "imported")
        self.assertGreater(self.vector_store.count_embeddings(), 0)

    def test_import_duplicate_no_new_embedding(self) -> None:
        f = Path(self.temp_dir.name) / "dup_emb.txt"
        f.write_text("Duplicate embedding test.", encoding="utf-8")
        r1 = self.service.import_document(f)
        count_before = self.vector_store.count_embeddings()
        r2 = self.service.import_document(f)
        self.assertEqual(r2.status, "duplicate")
        self.assertEqual(self.vector_store.count_embeddings(), count_before)


# ---- API Tests ----

class SearchApiTests(unittest.TestCase):
    """Tests for M4.4 Search API routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-search-api-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.vector_store = VectorStore(self.database_path)
        self.provider = LocalEmbeddingProvider(dimensions=64)
        self.engine = HybridSearchEngine(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_provider=self.provider,
        )
        self.request = MagicMock()
        self.request.app.state.knowledge_repository = self.repository
        self.request.app.state.vector_store = self.vector_store
        self.request.app.state.embedding_provider = self.provider

        self.domain = self.repository.create_domain(
            name="API Domain", slug="api-domain"
        )
        self.repository.create_item(
            title="Hybrid Search Test",
            content="This is a test for hybrid search functionality.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
            tags=[],
            importance=3,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_api_hybrid_search(self) -> None:
        payload = HybridSearchRequest(
            query="hybrid search test", limit=10
        )
        result = hybrid_search(payload, self.engine)
        self.assertEqual(result["query"], "hybrid search test")
        self.assertGreaterEqual(len(result["results"]), 1)
        self.assertEqual(result["offset"], 0)
        self.assertEqual(result["limit"], 10)

    def test_api_semantic_search(self) -> None:
        payload = HybridSearchRequest(
            query="search functionality test", limit=10
        )
        result = semantic_search(payload, self.engine)
        self.assertEqual(result["query"], "search functionality test")
        # All results should have ft_score=None (semantic only)
        for item in result["results"]:
            self.assertIsNone(item.ft_score)

    def test_api_search_status(self) -> None:
        result = search_status(self.engine)
        self.assertEqual(result["embedding_provider"], "local-hash")
        self.assertTrue(result["fts5_available"])

    def test_api_hybrid_search_empty_query(self) -> None:
        payload = HybridSearchRequest(query="zzznonexistentterm", limit=10)
        result = hybrid_search(payload, self.engine)
        self.assertEqual(result["results"], [])

    def test_api_hybrid_search_filter_domain(self) -> None:
        payload = HybridSearchRequest(
            query="test", domain_id=self.domain["id"], limit=10
        )
        result = hybrid_search(payload, self.engine)
        for item in result["results"]:
            self.assertEqual(item.domain_id, self.domain["id"])


if __name__ == "__main__":
    unittest.main()
