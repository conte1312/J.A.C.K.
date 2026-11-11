"""J.A.C.K. M4 Knowledge Repository tests.

Tests for SQLite-backed persistent knowledge repository using the
separate knowledge.sqlite3 database (independent from M3's memories.sqlite3).

CRUD, search, filters, relations, audit log, approval flow,
migrations, persistence, and backup.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from app.knowledge.repository import (
    DuplicateMemoryLinkError,
    KnowledgeNotFoundError,
    KnowledgeProposalConflictError,
    KnowledgeRepository,
    SCHEMA_VERSION,
    default_knowledge_database_path,
)


class KnowledgeRepositoryTests(unittest.TestCase):
    """Tests for the M4 Knowledge Repository using knowledge.sqlite3."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-knowledge-repository-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "knowledge.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    # ---- Schema and migrations ----

    def test_new_database_initializes_at_schema_v1(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        self.assertEqual(repository.current_version(), SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, 1)

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, SCHEMA_VERSION)

            # Required M4 tables exist
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            required_tables = {
                "knowledge_domains",
                "knowledge_items",
                "knowledge_versions",
                "knowledge_sources",
                "document_chunks",
                "knowledge_links",
                "knowledge_proposals",
                "knowledge_audit_log",
                "knowledge_settings",
            }
            self.assertTrue(required_tables.issubset(tables))

    def test_database_is_separate_from_m3(self) -> None:
        """Verify knowledge.sqlite3 is a distinct path from M3's memories.sqlite3."""
        knowledge_path = default_knowledge_database_path()
        from app.memory.repository import default_memory_database_path

        memory_path = default_memory_database_path()
        self.assertNotEqual(str(knowledge_path), str(memory_path))
        self.assertEqual(knowledge_path.name, "knowledge.sqlite3")
        self.assertEqual(memory_path.name, "memories.sqlite3")

    def test_database_file_is_private(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        if os.name != "nt":
            self.assertEqual(
                stat.S_IMODE(self.database_path.stat().st_mode), 0o600
            )

    def test_persistence_after_reinitialize(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(
            name="Work", slug="work", description="Work domain"
        )
        created = repository.create_item(
            title="Persistent knowledge",
            content="This should survive restart.",
            domain_id=domain["id"],
        )
        item_id = created["id"]

        repository2 = KnowledgeRepository(self.database_path)
        repository2.initialize()
        retrieved = repository2.get_item(item_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Persistent knowledge")
        self.assertEqual(retrieved["content"], "This should survive restart.")

    # ---- CRUD: Domains ----

    def test_create_and_get_domain(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(
            name="Work", slug="work", description="Work domain"
        )
        self.assertIsNotNone(domain["id"])
        self.assertEqual(domain["name"], "Work")
        self.assertEqual(domain["slug"], "work")
        self.assertEqual(domain["description"], "Work domain")

        retrieved = repository.get_domain(domain["id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], domain["id"])
        self.assertEqual(retrieved["slug"], "work")

    def test_create_domain_duplicate_slug_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        repository.create_domain(name="Work", slug="work")
        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_domain(name="Work Again", slug="work")

    def test_list_domains(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        repository.create_domain(name="Alpha", slug="alpha")
        repository.create_domain(name="Beta", slug="beta")
        repository.create_domain(name="Gamma", slug="gamma")

        domains = repository.list_domains()
        self.assertEqual(len(domains), 3)

    def test_update_and_delete_domain(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Old", slug="old")
        updated = repository.update_domain(domain["id"], name="New", slug="new")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["name"], "New")
        self.assertEqual(updated["slug"], "new")

        result = repository.delete_domain(domain["id"])
        self.assertTrue(result)
        self.assertIsNone(repository.get_domain(domain["id"]))

    def test_delete_nonexistent_domain_returns_false(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        result = repository.delete_domain("nonexistent-id")
        self.assertFalse(result)

    # ---- CRUD: Items ----

    def test_create_and_get_item(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(
            name="Work", slug="work", description="Work domain"
        )
        created = repository.create_item(
            title="Test knowledge",
            content="Test content",
            domain_id=domain["id"],
            knowledge_type="concept",
            source_type="system",
            tags=["alpha", "beta"],
            importance=4,
        )
        self.assertIsNotNone(created["id"])
        self.assertEqual(created["title"], "Test knowledge")
        self.assertEqual(created["content"], "Test content")
        self.assertEqual(created["knowledge_type"], "concept")
        self.assertEqual(created["source_type"], "system")
        self.assertEqual(created["tags"], ["alpha", "beta"])
        self.assertEqual(created["importance"], 4)
        self.assertFalse(created["excluded"])
        self.assertEqual(created["created_at"], created["updated_at"])

        retrieved = repository.get_item(created["id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], created["id"])
        self.assertEqual(retrieved["title"], "Test knowledge")

    def test_create_requires_valid_domain(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        with self.assertRaises(KnowledgeNotFoundError):
            repository.create_item(
                title="Bad",
                content="Bad domain",
                domain_id="not_a_domain",
            )

    def test_create_invalid_knowledge_type_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        with self.assertRaises(ValueError):
            repository.create_item(
                title="Bad",
                content="Bad type",
                domain_id=domain["id"],
                knowledge_type="invalid_type",
            )

    def test_create_invalid_importance_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        with self.assertRaises(ValueError):
            repository.create_item(
                title="Bad",
                content="Bad importance",
                domain_id=domain["id"],
                importance=10,
            )

    def test_create_invalid_confidence_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        with self.assertRaises(ValueError):
            repository.create_item(
                title="Bad",
                content="Bad confidence",
                domain_id=domain["id"],
                confidence_score=1.5,
            )

    def test_update_item(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="Original",
            content="Original content",
            domain_id=domain["id"],
            knowledge_type="concept",
        )
        updated = repository.update_item(
            created["id"],
            title="Updated title",
            content="Updated content",
            knowledge_type="concept",
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["title"], "Updated title")
        self.assertEqual(updated["content"], "Updated content")
        self.assertEqual(updated["knowledge_type"], "concept")
        self.assertNotEqual(updated["updated_at"], created["updated_at"])
        self.assertGreater(updated["updated_at"], created["updated_at"])
        self.assertEqual(updated["version"], 2)

    def test_update_creates_version_record(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="Original",
            content="Original content",
            domain_id=domain["id"],
        )
        repository.update_item(created["id"], title="Updated")

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            versions = connection.execute(
                "SELECT COUNT(*) AS cnt FROM knowledge_versions WHERE item_id = ?",
                (created["id"],),
            ).fetchone()["cnt"]
            self.assertGreaterEqual(versions, 1)

    def test_update_nonexistent_item_returns_none(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        result = repository.update_item("nonexistent-id", title="Nope")
        self.assertIsNone(result)

    def test_delete_item_archives(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="To archive",
            content="Will be archived",
            domain_id=domain["id"],
        )
        result = repository.delete_item(created["id"])
        self.assertTrue(result)
        archived = repository.get_item(created["id"])
        self.assertIsNotNone(archived)
        self.assertEqual(archived["item_state"], "archived")

    def test_delete_nonexistent_item_returns_false(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        result = repository.delete_item("nonexistent-id")
        self.assertFalse(result)

    # ---- Search and filters ----

    def test_search_items(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(
            title="Project Alpha meeting",
            content="Discuss quarterly goals",
            domain_id=domain["id"],
            knowledge_type="concept",
        )
        repository.create_item(
            title="Grocery list",
            content="Milk, eggs, bread",
            domain_id=domain["id"],
            knowledge_type="concept",
        )

        results = repository.search_items("meeting")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Project Alpha meeting")

        results = repository.search_items("eggs")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Grocery list")

    def test_filter_by_knowledge_type(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(
            title="Work item",
            content="Work content",
            domain_id=domain["id"],
            knowledge_type="concept",
        )
        repository.create_item(
            title="Pref item",
            content="Pref content",
            domain_id=domain["id"],
            knowledge_type="fact",
        )

        concept_items = repository.list_items(knowledge_type="concept")
        self.assertEqual(len(concept_items), 1)
        self.assertEqual(concept_items[0]["title"], "Work item")

    def test_filter_by_verification_status(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(
            title="Verified item",
            content="Content",
            domain_id=domain["id"],
            verification_status="verified",
        )
        repository.create_item(
            title="Unverified item",
            content="Content",
            domain_id=domain["id"],
            verification_status="unverified",
        )

        verified = repository.list_items(verification_status="verified")
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0]["title"], "Verified item")

    def test_filter_by_item_state(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(
            title="Draft item",
            content="Content",
            domain_id=domain["id"],
            item_state="draft",
        )
        repository.create_item(
            title="Published item",
            content="Content",
            domain_id=domain["id"],
            item_state="published",
        )

        drafts = repository.list_items(item_state="draft")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["title"], "Draft item")

    # ---- Relations ----

    def test_create_link(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(
            title="A", content="A content", domain_id=domain["id"]
        )
        b = repository.create_item(
            title="B", content="B content", domain_id=domain["id"]
        )

        link = repository.create_link(
            from_id=a["id"],
            to_id=b["id"],
            relation_type="related",
            strength=2,
        )
        self.assertIsNotNone(link["id"])
        self.assertEqual(link["from_id"], a["id"])
        self.assertEqual(link["to_id"], b["id"])
        self.assertEqual(link["relation_type"], "related")
        self.assertEqual(link["strength"], 2)

    def test_create_self_link_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(
            title="A", content="A content", domain_id=domain["id"]
        )
        with self.assertRaises(ValueError):
            repository.create_link(
                from_id=a["id"],
                to_id=a["id"],
                relation_type="related",
                strength=2,
            )

    def test_create_link_invalid_relation_type_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        with self.assertRaises(ValueError):
            repository.create_link(
                from_id=a["id"],
                to_id=b["id"],
                relation_type="invalid_relation",
                strength=2,
            )

    def test_create_link_invalid_strength_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        with self.assertRaises(ValueError):
            repository.create_link(
                from_id=a["id"],
                to_id=b["id"],
                relation_type="related",
                strength=10,
            )

    def test_create_link_nonexistent_item_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        with self.assertRaises(KnowledgeNotFoundError):
            repository.create_link(
                from_id="nonexistent-1",
                to_id="nonexistent-2",
                relation_type="related",
                strength=2,
            )

    def test_get_links(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        c = repository.create_item(title="C", content="C", domain_id=domain["id"])

        repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=2
        )
        repository.create_link(
            from_id=a["id"], to_id=c["id"], relation_type="supports", strength=1
        )
        repository.create_link(
            from_id=b["id"], to_id=c["id"], relation_type="related", strength=3
        )

        outgoing = repository.list_links(item_id=a["id"])
        self.assertEqual(len(outgoing), 2)
        outgoing_ids = {link["to_id"] for link in outgoing}
        self.assertIn(b["id"], outgoing_ids)
        self.assertIn(c["id"], outgoing_ids)

        incoming = repository.list_links(item_id=c["id"])
        self.assertEqual(len(incoming), 2)
        incoming_ids = {link["from_id"] for link in incoming}
        self.assertIn(a["id"], incoming_ids)
        self.assertIn(b["id"], incoming_ids)

    def test_list_links_by_relation_type(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        c = repository.create_item(title="C", content="C", domain_id=domain["id"])

        repository.create_link(from_id=a["id"], to_id=b["id"], relation_type="supports", strength=1)
        repository.create_link(from_id=a["id"], to_id=c["id"], relation_type="supports", strength=2)
        repository.create_link(from_id=b["id"], to_id=c["id"], relation_type="related", strength=3)

        supports_links = repository.list_links(relation_type="supports")
        self.assertEqual(len(supports_links), 2)

    def test_duplicate_link_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])

        repository.create_link(
            from_id=a["id"],
            to_id=b["id"],
            relation_type="related",
            strength=2,
        )
        with self.assertRaises(DuplicateMemoryLinkError):
            repository.create_link(
                from_id=a["id"],
                to_id=b["id"],
                relation_type="related",
                strength=2,
            )

    def test_delete_link(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])

        link = repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        result = repository.delete_link(link["id"])
        self.assertTrue(result)
        self.assertIsNone(repository.get_link(link["id"]))

    def test_delete_nonexistent_link_returns_false(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        result = repository.delete_link("nonexistent-id")
        self.assertFalse(result)

    # ---- Proposals ----

    def test_create_and_get_proposal(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        proposal = repository.create_proposal(
            title="Proposed knowledge",
            content="Proposed content",
            domain_id=domain["id"],
        )
        self.assertIsNotNone(proposal["id"])
        self.assertEqual(proposal["title"], "Proposed knowledge")
        self.assertEqual(proposal["process_state"], "pending")
        self.assertIsNotNone(proposal["expires_at"])

        retrieved = repository.get_proposal(proposal["id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], proposal["id"])
        self.assertEqual(retrieved["process_state"], "pending")

    def test_list_proposals(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_proposal(title="P1", content="C1", domain_id=domain["id"])
        repository.create_proposal(title="P2", content="C2", domain_id=domain["id"])

        proposals = repository.list_proposals()
        self.assertEqual(len(proposals), 2)

        pending = repository.list_proposals(process_state="pending")
        self.assertEqual(len(pending), 2)

    def test_get_nonexistent_proposal_returns_none(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        result = repository.get_proposal("nonexistent-id")
        self.assertIsNone(result)

    def test_approve_proposal_creates_item(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        proposal = repository.create_proposal(
            title="To approve",
            content="Content",
            domain_id=domain["id"],
        )
        item = repository.approve_proposal(proposal["id"])
        self.assertIsNotNone(item)
        self.assertEqual(item["title"], "To approve")
        self.assertEqual(item["item_state"], "published")

        # Proposal should now be published
        updated_proposal = repository.get_proposal(proposal["id"])
        self.assertEqual(updated_proposal["process_state"], "published")
        self.assertEqual(updated_proposal["published_item_id"], item["id"])

    def test_reject_proposal(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        proposal = repository.create_proposal(
            title="To reject",
            content="Content",
            domain_id=domain["id"],
        )
        result = repository.reject_proposal(proposal["id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["process_state"], "rejected")

        updated_proposal = repository.get_proposal(proposal["id"])
        self.assertEqual(updated_proposal["process_state"], "rejected")

    def test_approve_already_processed_proposal_raises(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        proposal = repository.create_proposal(
            title="Already processed",
            content="Content",
            domain_id=domain["id"],
        )
        repository.approve_proposal(proposal["id"])
        with self.assertRaises(KnowledgeProposalConflictError):
            repository.approve_proposal(proposal["id"])

    # ---- Audit log ----

    def test_audit_log_tracks_create(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="Audit test",
            content="Content",
            domain_id=domain["id"],
        )
        audit = repository.audit_log(item_id=created["id"])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["action"], "knowledge.created")
        self.assertEqual(audit[0]["item_id"], created["id"])

    def test_audit_log_tracks_update(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="Before",
            content="Content",
            domain_id=domain["id"],
        )
        repository.update_item(created["id"], title="After")
        audit = repository.audit_log(item_id=created["id"])
        actions = [entry["action"] for entry in audit]
        self.assertIn("knowledge.created", actions)
        self.assertIn("knowledge.updated", actions)

    def test_audit_log_tracks_proposal(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        proposal = repository.create_proposal(
            title="Audit proposal",
            content="Content",
            domain_id=domain["id"],
        )
        audit = repository.audit_log(proposal_id=proposal["id"])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["action"], "proposal.created")

    def test_audit_log_filter_by_action(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created_a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        created_b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        repository.update_item(created_a["id"], title="A2")

        create_entries = repository.audit_log(action="knowledge.created")
        self.assertEqual(len(create_entries), 2)
        update_entries = repository.audit_log(action="knowledge.updated")
        self.assertEqual(len(update_entries), 1)

    def test_audit_log_immutability_trigger(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        created = repository.create_item(
            title="Audit", content="Content", domain_id=domain["id"]
        )
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id FROM knowledge_audit_log WHERE item_id = ? LIMIT 1",
                (created["id"],),
            ).fetchone()
            audit_id = row["id"]

        # Attempt to update audit log - should fail (immutable)
        with sqlite3.connect(self.database_path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE knowledge_audit_log SET action = 'tampered' WHERE id = ?",
                    (audit_id,),
                )

        # Attempt to delete audit log - should fail (immutable)
        with sqlite3.connect(self.database_path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM knowledge_audit_log WHERE id = ?", (audit_id,)
                )

    # ---- Referential integrity ----

    def test_delete_domain_restricts_when_items_exist(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(
            title="Item in domain",
            content="Content",
            domain_id=domain["id"],
        )
        # Should fail because items reference this domain (ON DELETE RESTRICT)
        with self.assertRaises(sqlite3.IntegrityError):
            repository.delete_domain(domain["id"])

    def test_delete_item_archives_and_preserves_links(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        a = repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = repository.create_item(title="B", content="B", domain_id=domain["id"])
        link = repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        repository.delete_item(a["id"])
        # Soft delete archives the item but preserves links (ON DELETE CASCADE
        # only triggers on hard DELETE, not UPDATE)
        archived = repository.get_item(a["id"])
        self.assertIsNotNone(archived)
        self.assertEqual(archived["item_state"], "archived")
        # Link still exists because item was archived, not hard-deleted
        self.assertIsNotNone(repository.get_link(link["id"]))

    # ---- Backup ----

    def test_backup_before_migration_creates_file(self) -> None:
        repository = KnowledgeRepository(self.database_path)
        repository.initialize()
        domain = repository.create_domain(name="Work", slug="work")
        repository.create_item(title="Before", content="Content", domain_id=domain["id"])

        # Simulate migration by re-initializing (backup should be created)
        # Since we're already at v1, no migration runs. Test the backup path directly.
        with sqlite3.connect(self.database_path) as connection:
            backup_path = repository._backup_before_migration(connection)
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.name, "knowledge.sqlite3.pre-v1.bak")


if __name__ == "__main__":
    unittest.main()