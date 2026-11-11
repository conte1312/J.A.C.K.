"""J.A.C.K. M4.6 Context Builder tests.

Tests for ContextualResolver, ContextBuilder, and Context API.
Uses isolated temporary databases. Never touches real user data.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.api.routes.v2.knowledge import build_context, resolve_context
from app.api.schemas.knowledge import ContextBuildRequest
from app.knowledge.context_builder import ContextBuilder
from app.knowledge.context_resolver import ContextualResolver
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.m3_interface import MemoryReadInterface
from app.knowledge.repository import KnowledgeRepository


def _make_request(repository: KnowledgeRepository) -> MagicMock:
    request = MagicMock()
    request.app.state.knowledge_repository = repository
    return request


class ContextualResolverTests(unittest.TestCase):
    """Tests for ContextualResolver (M4.6)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-resolver-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.resolver = ContextualResolver(repository=self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_empty_query(self) -> None:
        plan = self.resolver.resolve(query="")
        self.assertEqual(plan.query, "")
        self.assertEqual(plan.key_terms, [])
        self.assertEqual(plan.relevant_domains, [])
        self.assertFalse(plan.include_graph)

    def test_resolve_key_terms(self) -> None:
        plan = self.resolver.resolve(query="Project Alpha meeting notes")
        self.assertIn("project", plan.key_terms)
        self.assertIn("alpha", plan.key_terms)
        self.assertIn("meeting", plan.key_terms)
        self.assertIn("notes", plan.key_terms)

    def test_resolve_domain_detection(self) -> None:
        plan = self.resolver.resolve(query="Project deadline meeting with client")
        self.assertIn("work", plan.relevant_domains)

    def test_resolve_item_type_detection(self) -> None:
        plan = self.resolver.resolve(query="How to configure the server")
        self.assertIn("procedure", plan.relevant_item_types)

    def test_resolve_graph_trigger(self) -> None:
        plan = self.resolver.resolve(query="What is related to this project")
        self.assertTrue(plan.include_graph)

    def test_resolve_no_graph_trigger(self) -> None:
        plan = self.resolver.resolve(query="What is the definition of X")
        self.assertFalse(plan.include_graph)

    def test_resolve_with_domain(self) -> None:
        plan = self.resolver.resolve(
            query="test query", domain_id="explicit-domain"
        )
        self.assertEqual(plan.relevant_domains, ["explicit-domain"])


class ContextBuilderTests(unittest.TestCase):
    """Tests for ContextBuilder (M4.6)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-builder-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.builder = ContextBuilder(repository=self.repository)

        self.domain = self.repository.create_domain(
            name="Builder Domain", slug="builder-domain"
        )
        self.item1 = self.repository.create_item(
            title="Python Tutorial", content="Learn Python programming basics.",
            domain_id=self.domain["id"],
            knowledge_type="procedure",
            source_type="document",
            verification_status="verified",
            item_state="published",
            tags=["python", "tutorial"],
            importance=4,
        )
        self.item2 = self.repository.create_item(
            title="Draft Note", content="Unverified draft content.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="system",
            verification_status="unverified",
            item_state="draft",
            tags=["draft"],
            importance=2,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_context_basic(self) -> None:
        package = self.builder.build_context(
            query="Python tutorial", max_items=5
        )
        self.assertEqual(package.query, "Python tutorial")
        self.assertGreaterEqual(package.total_items, 1)
        self.assertGreater(package.token_budget, 0)
        self.assertEqual(package.context_version, "1.0")

    def test_build_context_item_fields(self) -> None:
        package = self.builder.build_context(
            query="Python tutorial", max_items=5
        )
        self.assertGreaterEqual(len(package.items), 1)
        item = package.items[0]
        self.assertEqual(item.item_id, self.item1["id"])
        self.assertEqual(item.title, "Python Tutorial")
        self.assertEqual(item.verification_status, "verified")
        self.assertGreater(item.confidence, 0.5)
        self.assertFalse(item.is_personal)

    def test_build_context_token_budget(self) -> None:
        package = self.builder.build_context(
            query="Python tutorial", max_items=5,
            target_model_context=1000,
        )
        self.assertLessEqual(package.total_tokens_estimated, package.token_budget)

    def test_build_context_verification_summary(self) -> None:
        package = self.builder.build_context(
            query="Python", max_items=10
        )
        self.assertIsInstance(package.verification_summary, dict)
        self.assertGreater(sum(package.verification_summary.values()), 0)

    def test_build_context_no_items(self) -> None:
        package = self.builder.build_context(
            query="zzznonexistenttermxyz", max_items=5
        )
        self.assertEqual(package.total_items, 0)
        self.assertEqual(package.total_tokens_estimated, 0)

    def test_build_context_with_personal_no_m3(self) -> None:
        # include_personal=True but no M3 interface configured
        package = self.builder.build_context(
            query="test", include_personal=True
        )
        # Should not crash; personal items simply not added
        self.assertIsInstance(package.total_items, int)

    def test_build_context_generated_at(self) -> None:
        package = self.builder.build_context(query="test", max_items=5)
        self.assertIsNotNone(package.generated_at)
        self.assertIn("T", package.generated_at)  # ISO format


class M3InterfaceTests(unittest.TestCase):
    """Tests for M3 read-only interface protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        from app.knowledge.m3_interface import MemoryReadInterface
        self.assertTrue(hasattr(MemoryReadInterface, "__protocol__") or
                        hasattr(MemoryReadInterface, "_is_protocol"))

    def test_mock_implements_interface(self) -> None:
        from app.knowledge.m3_interface import MemoryReadInterface

        class FakeMemory:
            def get_item(self, item_id):
                return {"id": item_id, "title": "Test"}

            def list_items(self, **kwargs):
                return []

            def search_items(self, query, **kwargs):
                return []

            def audit_log(self, **kwargs):
                return []

        fake = FakeMemory()
        self.assertTrue(isinstance(fake, MemoryReadInterface))


class ContextApiTests(unittest.TestCase):
    """Tests for M4.6 Context API routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-context-api-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.builder = ContextBuilder(repository=self.repository)
        self.request = _make_request(self.repository)

        self.domain = self.repository.create_domain(
            name="Context API Domain", slug="context-api-domain"
        )
        self.repository.create_item(
            title="Context Test Item", content="Context building test content.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_api_resolve_context(self) -> None:
        payload = ContextBuildRequest(
            query="Context test", max_items=5
        )
        result = resolve_context(payload, self.builder)
        self.assertEqual(result["query"], "Context test")
        self.assertIsInstance(result["key_terms"], list)
        self.assertIsInstance(result["reason"], str)

    def test_api_build_context(self) -> None:
        payload = ContextBuildRequest(
            query="Context test", max_items=5
        )
        result = build_context(payload, self.builder)
        self.assertEqual(result["query"], "Context test")
        self.assertGreaterEqual(result["total_items"], 1)
        self.assertGreater(result["token_budget"], 0)
        self.assertIsInstance(result["verification_summary"], dict)
        self.assertIsInstance(result["sources"], list)
        self.assertIsInstance(result["uncertainty_notes"], list)
        self.assertIsNotNone(result["generated_at"])

    def test_api_build_context_with_budget(self) -> None:
        payload = ContextBuildRequest(
            query="Context test", max_items=5,
            target_model_context=2000,
        )
        result = build_context(payload, self.builder)
        self.assertLessEqual(
            result["total_tokens_estimated"], result["token_budget"]
        )

    def test_api_build_context_empty_query(self) -> None:
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            ContextBuildRequest(query="")


if __name__ == "__main__":
    unittest.main()
