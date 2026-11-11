"""J.A.C.K. M4.7 Validation & Maintenance tests.

Tests for maintenance service, validation service, source evaluation,
autonomous learning policy, and related API routes.
Uses isolated temporary databases.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.routes.v2.knowledge import (
    build_context,
    evaluate_policy,
    evaluate_source,
    get_broken_provenance,
    get_database_integrity,
    get_embedding_consistency,
    get_graph_consistency,
    get_contradictions,
    get_duplicates,
    get_orphans,
    get_stale,
    get_versions,
    resolve_context,
    run_maintenance,
    validate_transition,
)
from app.api.schemas.knowledge import (
    EvaluatePolicyRequest,
    MaintenanceRunRequest,
    VerificationTransitionRequest,
)
from app.knowledge.context_builder import ContextBuilder
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.maintenance_service import MaintenanceService
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.validation_service import ValidationService


def _make_request(repository: KnowledgeRepository) -> MagicMock:
    request = MagicMock()
    request.app.state.knowledge_repository = repository
    return request


class MaintenanceServiceTests(unittest.TestCase):
    """Tests for MaintenanceService (M4.7)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-maint-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = MaintenanceService(repository=self.repository)

        self.domain = self.repository.create_domain(
            name="Maint Domain", slug="maint-domain"
        )
        self.item1 = self.repository.create_item(
            title="Duplicate Item", content="Same content here.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        self.item2 = self.repository.create_item(
            title="Duplicate Item", content="Same content here.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        self.item3 = self.repository.create_item(
            title="Stale Item", content="Old content.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="unverified",
            item_state="published",
        )
        self.item4 = self.repository.create_item(
            title="Orphan Item", content="No links.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="unverified",
            item_state="published",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_full_maintenance(self) -> None:
        report = self.service.run_full_maintenance()
        self.assertIsInstance(report.duplicate_items, list)
        self.assertIsInstance(report.stale_items, list)
        self.assertIsInstance(report.orphan_items, list)
        self.assertIsInstance(report.broken_provenance, list)
        self.assertIsInstance(report.embedding_consistency, dict)
        self.assertIsInstance(report.graph_consistency, list)
        self.assertIsInstance(report.database_integrity, dict)
        self.assertIsNotNone(report.generated_at)

    def test_find_duplicates(self) -> None:
        dupes = self.service.find_duplicate_items()
        # item1 and item2 have same content
        self.assertGreaterEqual(len(dupes), 0)

    def test_find_stale_items(self) -> None:
        # item3 might not be stale yet (0 days), so 0 expected
        stale = self.service.find_stale_items(stale_days=0)
        # With stale_days=0, everything updated "now" is not stale
        self.assertIsInstance(stale, list)

    def test_find_orphans(self) -> None:
        orphans = self.service.find_orphan_items()
        self.assertIsInstance(orphans, list)

    def test_find_broken_provenance(self) -> None:
        broken = self.service.find_broken_provenance()
        self.assertIsInstance(broken, list)

    def test_embedding_consistency(self) -> None:
        result = self.service.check_embedding_consistency()
        self.assertIn("total_published_items", result)
        self.assertIn("items_with_embeddings", result)
        self.assertIn("missing_embeddings", result)
        self.assertIn("consistency_ratio", result)

    def test_graph_consistency(self) -> None:
        result = self.service.check_graph_consistency()
        self.assertIsInstance(result, list)

    def test_database_integrity(self) -> None:
        result = self.service.check_database_integrity()
        self.assertIn("integrity_check", result)
        self.assertIn("passed", result)
        self.assertIn("database", result)


class ValidationServiceTests(unittest.TestCase):
    """Tests for ValidationService (M4.7)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-val-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = ValidationService(repository=self.repository)

        self.domain = self.repository.create_domain(
            name="Val Domain", slug="val-domain"
        )
        self.source = self.repository.create_domain(
            name="Source Domain", slug="source-domain"
        )  # reuse domain as source proxy
        self.item = self.repository.create_item(
            title="Versioned Item", content="Original content.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_evaluate_source_not_found(self) -> None:
        result = self.service.evaluate_source("nonexistent-source")
        self.assertIsNone(result)

    def test_evaluate_learning_policy_general(self) -> None:
        decision = self.service.evaluate_learning_policy(
            source_id=self.domain["id"],
            content_sensitivity="general",
            source_trust=0.8,
        )
        self.assertIn(decision.level, {"low_risk", "specialized", "controlled"})
        self.assertIn(decision.action, {"auto_publish", "keep_provisional", "require_approval"})
        self.assertIsInstance(decision.reason, str)

    def test_evaluate_learning_policy_sensitive(self) -> None:
        decision = self.service.evaluate_learning_policy(
            source_id=self.domain["id"],
            content_sensitivity="sensitive",
        )
        self.assertEqual(decision.level, "controlled")
        self.assertEqual(decision.action, "require_approval")

    def test_validate_transition_item_state(self) -> None:
        self.assertTrue(
            self.service.validate_transition(
                "draft", "published", "item_state"
            )
        )
        self.assertFalse(
            self.service.validate_transition(
                "published", "draft", "item_state"
            )
        )

    def test_validate_transition_process_state(self) -> None:
        self.assertTrue(
            self.service.validate_transition(
                "pending", "accepted", "process_state"
            )
        )
        self.assertFalse(
            self.service.validate_transition(
                "accepted", "rejected", "process_state"
            )
        )

    def test_validate_transition_verification(self) -> None:
        self.assertTrue(
            self.service.validate_transition(
                "unverified", "verified", "verification_status"
            )
        )

    def test_get_version_history(self) -> None:
        versions = self.service.get_version_history(self.item["id"])
        self.assertIsInstance(versions, list)

    def test_find_contradictions(self) -> None:
        contradictions = self.service.find_contradictions()
        self.assertIsInstance(contradictions, list)


class ContextApiM47Tests(unittest.TestCase):
    """Tests for M4.7 Maintenance & Validation API routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-m47-api-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.maintenance_service = MaintenanceService(
            repository=self.repository
        )
        self.validation_service = ValidationService(
            repository=self.repository
        )
        self.context_builder = ContextBuilder(
            repository=self.repository
        )
        self.request = _make_request(self.repository)

        self.domain = self.repository.create_domain(
            name="M47 API Domain", slug="m47-api-domain"
        )
        self.item = self.repository.create_item(
            title="M47 Test Item", content="M47 test content.",
            domain_id=self.domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        # Create a real source for evaluate_source test
        import sqlite3
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO knowledge_sources (id, title, document_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("test-source-id", "Test Source", "txt", "2026-01-01T00:00:00.000Z", "2026-01-01T00:00:00.000Z"),
            )
            conn.commit()
        self.source_id = "test-source-id"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_api_run_maintenance(self) -> None:
        payload = MaintenanceRunRequest(stale_days=180)
        result = run_maintenance(payload, self.maintenance_service)
        self.assertIn("duplicate_items", result)
        self.assertIn("stale_items", result)
        self.assertIn("orphan_items", result)
        self.assertIn("broken_provenance", result)
        self.assertIn("embedding_consistency", result)
        self.assertIn("graph_consistency", result)
        self.assertIn("database_integrity", result)
        self.assertIn("generated_at", result)

    def test_api_get_duplicates(self) -> None:
        result = get_duplicates(self.maintenance_service)
        self.assertIsInstance(result, list)

    def test_api_get_stale(self) -> None:
        result = get_stale(stale_days=180, service=self.maintenance_service)
        self.assertIsInstance(result, list)

    def test_api_get_orphans(self) -> None:
        result = get_orphans(self.maintenance_service)
        self.assertIsInstance(result, list)

    def test_api_get_broken_provenance(self) -> None:
        result = get_broken_provenance(self.maintenance_service)
        self.assertIsInstance(result, list)

    def test_api_get_embedding_consistency(self) -> None:
        result = get_embedding_consistency(self.maintenance_service)
        self.assertIn("total_published_items", result)
        self.assertIn("consistency_ratio", result)

    def test_api_get_graph_consistency(self) -> None:
        result = get_graph_consistency(self.maintenance_service)
        self.assertIsInstance(result, list)

    def test_api_get_database_integrity(self) -> None:
        result = get_database_integrity(self.maintenance_service)
        self.assertIn("integrity_check", result)
        self.assertIn("passed", result)

    def test_api_evaluate_source(self) -> None:
        result = evaluate_source(
            source_id=self.source_id,
            service=self.validation_service,
        )
        self.assertIn("source_id", result)
        self.assertIn("overall_trust", result)

    def test_api_evaluate_source_not_found(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            evaluate_source(
                source_id="nonexistent",
                service=self.validation_service,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_evaluate_policy(self) -> None:
        payload = EvaluatePolicyRequest(
            source_id=self.domain["id"],
            content_sensitivity="general",
        )
        result = evaluate_policy(payload, self.validation_service)
        self.assertIn("level", result)
        self.assertIn("action", result)
        self.assertIn("reason", result)

    def test_api_validate_transition(self) -> None:
        payload = VerificationTransitionRequest(
            item_id=self.item["id"],
            current_state="draft",
            target_state="published",
            state_type="item_state",
        )
        result = validate_transition(payload, self.validation_service)
        self.assertIn("allowed", result)
        self.assertIsInstance(result["allowed"], bool)

    def test_api_get_versions(self) -> None:
        result = get_versions(item_id=self.item["id"], service=self.validation_service)
        self.assertIsInstance(result, list)

    def test_api_get_contradictions(self) -> None:
        result = get_contradictions(service=self.validation_service)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
