"""J.A.C.K. M4 Knowledge API tests.

Tests the FastAPI Knowledge API layer (M4.2) using isolated temporary
SQLite databases. Never touches the real user databases.

Coverage:
- Domains: create, list, retrieve, update, duplicate slug, invalid parent, delete restrictions.
- Items: create, retrieve, update, archive, list, filters, search, invalid input, missing item.
- Relations: create, outgoing, incoming, duplicate, invalid relation, self-link, delete.
- Proposals: create, list, retrieve, approve, reject, expiration, repeated approval, conflict, audit.
- Architecture: M4 uses knowledge.sqlite3, M3 uses memories.sqlite3, isolation, soft-delete, audit immutability.
"""

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes.v2.knowledge import (
    approve_proposal,
    archive_item,
    create_domain,
    create_item,
    create_link,
    create_proposal,
    delete_domain,
    delete_link,
    get_domain,
    get_item,
    get_link,
    get_proposal,
    knowledge_health,
    list_domains,
    list_items,
    list_links,
    list_proposals,
    reject_proposal,
    search_items,
    update_domain,
    update_item,
)
from app.api.schemas.knowledge import (
    DomainWrite,
    ItemUpdate,
    ItemWrite,
    LinkWrite,
    ProposalWrite,
)
from app.knowledge.repository import (
    DuplicateMemoryLinkError,
    KnowledgeNotFoundError,
    KnowledgeProposalConflictError,
    KnowledgeRepository,
    default_knowledge_database_path,
)


def _make_request(repository: KnowledgeRepository) -> MagicMock:
    """Crea un Request mock con il repository nello stato dell'app."""
    request = MagicMock()
    request.app.state.knowledge_repository = repository
    return request


class KnowledgeApiTests(unittest.TestCase):
    """Test per l'API M4 Knowledge su database temporaneo."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-knowledge-api-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.request = _make_request(self.repository)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    # ---- Domains ----

    def test_api_create_domain(self) -> None:
        payload = DomainWrite(name="Work", slug="work", description="Work domain")
        result = create_domain(payload, self.repository)
        self.assertEqual(result["name"], "Work")
        self.assertEqual(result["slug"], "work")
        self.assertEqual(result["description"], "Work domain")
        self.assertIsNotNone(result["id"])

    def test_api_list_domains(self) -> None:
        self.repository.create_domain(name="Alpha", slug="alpha")
        self.repository.create_domain(name="Beta", slug="beta")
        result = list_domains(self.repository)
        self.assertEqual(len(result), 2)

    def test_api_list_domains_by_parent(self) -> None:
        parent = self.repository.create_domain(name="Parent", slug="parent")
        child = self.repository.create_domain(
            name="Child", slug="child", parent_domain_id=parent["id"]
        )
        result = list_domains(
            self.repository, parent_domain_id=parent["id"]
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], child["id"])

    def test_api_get_domain(self) -> None:
        created = self.repository.create_domain(name="Work", slug="work")
        result = get_domain(created["id"], self.repository)
        self.assertIsNotNone(result)
        self.assertEqual(result["slug"], "work")

    def test_api_get_domain_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_domain("nonexistent", self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_update_domain(self) -> None:
        created = self.repository.create_domain(name="Old", slug="old")
        payload = DomainWrite(name="New", slug="new", description="Updated")
        result = update_domain(created["id"], payload, self.repository)
        self.assertEqual(result["name"], "New")
        self.assertEqual(result["slug"], "new")
        self.assertEqual(result["description"], "Updated")

    def test_api_update_domain_missing(self) -> None:
        payload = DomainWrite(name="New", slug="new")
        with self.assertRaises(HTTPException) as ctx:
            update_domain("nonexistent", payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_create_domain_duplicate_slug(self) -> None:
        self.repository.create_domain(name="Work", slug="work")
        payload = DomainWrite(name="Work2", slug="work")
        with self.assertRaises(HTTPException) as ctx:
            create_domain(payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_api_delete_domain_restrict(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_item(
            title="Item", content="Content", domain_id=domain["id"]
        )
        with self.assertRaises(sqlite3.IntegrityError):
            delete_domain(domain["id"], self.repository)

    def test_api_delete_domain(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        result = delete_domain(domain["id"], self.repository)
        self.assertTrue(result)
        self.assertIsNone(self.repository.get_domain(domain["id"]))

    def test_api_health_no_database_path(self) -> None:
        result = knowledge_health(self.repository)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["schema_version"], 1)
        self.assertNotIn("database", result)
        self.assertNotIn(str(self.database_path), str(result))

    def test_api_create_domain_duplicate_slug_409(self) -> None:
        self.repository.create_domain(name="Work", slug="work")
        payload = DomainWrite(name="Work2", slug="work")
        with self.assertRaises(HTTPException) as ctx:
            create_domain(payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_api_update_domain_nonexistent_404(self) -> None:
        payload = DomainWrite(name="New", slug="new")
        with self.assertRaises(HTTPException) as ctx:
            update_domain("nonexistent-id", payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_update_domain_duplicate_slug_409(self) -> None:
        alpha = self.repository.create_domain(name="Alpha", slug="alpha")
        beta = self.repository.create_domain(name="Beta", slug="beta")
        payload = DomainWrite(name="Beta Updated", slug="alpha")
        with self.assertRaises(HTTPException) as ctx:
            update_domain(beta["id"], payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    # ---- Items ----

    def test_api_create_item(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        payload = ItemWrite(
            title="Knowledge item",
            content="Content body",
            domain_id=domain["id"],
            knowledge_type="concept",
            source_type="system",
            tags=["alpha"],
            importance=4,
        )
        result = create_item(payload, self.repository)
        self.assertEqual(result["title"], "Knowledge item")
        self.assertEqual(result["content"], "Content body")
        self.assertEqual(result["knowledge_type"], "concept")
        self.assertEqual(result["tags"], ["alpha"])
        self.assertEqual(result["importance"], 4)
        self.assertEqual(result["item_state"], "draft")

    def test_api_create_item_missing_domain(self) -> None:
        payload = ItemWrite(
            title="Orphan", content="No domain", domain_id="nonexistent"
        )
        with self.assertRaises(HTTPException) as ctx:
            create_item(payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_get_item(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_item(
            title="Retrieve me", content="Content", domain_id=domain["id"]
        )
        result = get_item(created["id"], self.repository)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Retrieve me")

    def test_api_get_item_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_item("nonexistent", self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_update_item(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_item(
            title="Original", content="Original content", domain_id=domain["id"]
        )
        payload = ItemUpdate(title="Updated", content="Updated content")
        result = update_item(created["id"], payload, self.repository)
        self.assertEqual(result["title"], "Updated")
        self.assertEqual(result["content"], "Updated content")
        self.assertEqual(result["version"], 2)

    def test_api_update_item_missing(self) -> None:
        payload = ItemUpdate(title="Nope")
        with self.assertRaises(HTTPException) as ctx:
            update_item("nonexistent", payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_archive_item_soft_delete(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_item(
            title="To archive", content="Content", domain_id=domain["id"]
        )
        # Soft-delete via API (no physical deletion)
        archive_item(created["id"], self.repository)
        archived = self.repository.get_item(created["id"])
        self.assertIsNotNone(archived)
        self.assertEqual(archived["item_state"], "archived")

    def test_api_archive_item_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            archive_item("nonexistent", self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_list_items_filters(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_item(
            title="Concept A",
            content="Content A",
            domain_id=domain["id"],
            knowledge_type="concept",
            verification_status="verified",
            item_state="published",
            importance=4,
        )
        self.repository.create_item(
            title="Fact B",
            content="Content B",
            domain_id=domain["id"],
            knowledge_type="fact",
            verification_status="unverified",
            item_state="draft",
            importance=2,
        )

        concepts = list_items(
            self.repository, knowledge_type="concept"
        )
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]["title"], "Concept A")

        published = list_items(
            self.repository, item_state="published"
        )
        self.assertEqual(len(published), 1)

        verified = list_items(
            self.repository, verification_status="verified"
        )
        self.assertEqual(len(verified), 1)

    def test_api_list_items_importance_range(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_item(
            title="High", content="C", domain_id=domain["id"], importance=5
        )
        self.repository.create_item(
            title="Low", content="C", domain_id=domain["id"], importance=1
        )

        result = list_items(
            self.repository, importance_min=3, importance_max=4
        )
        self.assertEqual(len(result), 0)

        result = list_items(self.repository, importance_min=1, importance_max=5)
        self.assertEqual(len(result), 2)

    def test_api_list_items_excluded(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_item(
            title="Normal", content="C", domain_id=domain["id"], excluded=False
        )
        self.repository.create_item(
            title="Excluded", content="C", domain_id=domain["id"], excluded=True
        )

        result = list_items(self.repository, excluded=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Excluded")

    def test_api_search_items(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_item(
            title="Project Alpha",
            content="Quarterly goals",
            domain_id=domain["id"],
        )
        self.repository.create_item(
            title="Grocery",
            content="Milk eggs",
            domain_id=domain["id"],
        )

        result = search_items(self.repository, q="Alpha")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Project Alpha")

    def test_api_search_items_empty_query(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            search_items(self.repository, q="")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_api_create_item_invalid_input(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        with self.assertRaises(ValidationError):
            ItemWrite(
                title="Bad", content="Bad", domain_id=domain["id"], importance=10
            )

    # ---- Relations ----

    def test_api_create_link(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        payload = LinkWrite(
            from_id=a["id"],
            to_id=b["id"],
            relation_type="related",
            strength=2,
        )
        result = create_link(payload, self.repository)
        self.assertEqual(result["relation_type"], "related")
        self.assertEqual(result["strength"], 2)
        self.assertEqual(result["from_id"], a["id"])
        self.assertEqual(result["to_id"], b["id"])

    def test_api_list_links_outgoing(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        c = self.repository.create_item(title="C", content="C", domain_id=domain["id"])
        self.repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        self.repository.create_link(
            from_id=a["id"], to_id=c["id"], relation_type="supports", strength=2
        )
        result = list_links(self.repository, item_id=a["id"])
        self.assertEqual(len(result), 2)

    def test_api_list_links_incoming(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        self.repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        result = list_links(self.repository, item_id=b["id"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["from_id"], a["id"])

    def test_api_list_links_by_type(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        self.repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="supports", strength=1
        )
        result = list_links(self.repository, relation_type="supports")
        self.assertEqual(len(result), 1)

    def test_api_create_link_duplicate(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        self.repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        payload = LinkWrite(
            from_id=a["id"],
            to_id=b["id"],
            relation_type="related",
            strength=1,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_link(payload, self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_api_create_link_self_link(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        with self.assertRaises(ValidationError):
            LinkWrite(
                from_id=a["id"],
                to_id=a["id"],
                relation_type="related",
                strength=1,
            )

    def test_api_create_link_invalid_type(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        with self.assertRaises(ValidationError):
            LinkWrite(
                from_id=a["id"],
                to_id=b["id"],
                relation_type="invalid_type",
                strength=1,
            )

    def test_api_delete_link(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        a = self.repository.create_item(title="A", content="A", domain_id=domain["id"])
        b = self.repository.create_item(title="B", content="B", domain_id=domain["id"])
        link = self.repository.create_link(
            from_id=a["id"], to_id=b["id"], relation_type="related", strength=1
        )
        result = delete_link(link["id"], self.repository)
        self.assertTrue(result)
        self.assertIsNone(self.repository.get_link(link["id"]))

    def test_api_delete_link_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            delete_link("nonexistent", self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    # ---- Proposals ----

    def test_api_create_proposal(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        payload = ProposalWrite(
            title="Proposed item",
            content="Proposed content",
            domain_id=domain["id"],
        )
        result = create_proposal(payload, self.repository)
        self.assertEqual(result["title"], "Proposed item")
        self.assertEqual(result["process_state"], "pending")
        self.assertIsNotNone(result["expires_at"])

    def test_api_list_proposals(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        self.repository.create_proposal(title="P1", content="C1", domain_id=domain["id"])
        self.repository.create_proposal(title="P2", content="C2", domain_id=domain["id"])
        result = list_proposals(self.repository)
        self.assertEqual(len(result), 2)

    def test_api_get_proposal(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_proposal(
            title="Prop", content="Content", domain_id=domain["id"]
        )
        result = get_proposal(created["id"], self.repository)
        self.assertIsNotNone(result)
        self.assertEqual(result["process_state"], "pending")

    def test_api_get_proposal_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_proposal("nonexistent", self.repository)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_approve_proposal(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_proposal(
            title="To approve", content="Content", domain_id=domain["id"]
        )
        result = approve_proposal(created["id"], self.repository)
        self.assertIsNotNone(result)
        self.assertEqual(result["item_state"], "published")
        # Proposal should be published now
        updated = self.repository.get_proposal(created["id"])
        self.assertEqual(updated["process_state"], "published")

    def test_api_reject_proposal(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_proposal(
            title="To reject", content="Content", domain_id=domain["id"]
        )
        result = reject_proposal(created["id"], self.repository)
        self.assertIsNotNone(result)
        self.assertEqual(result["process_state"], "rejected")
        updated = self.repository.get_proposal(created["id"])
        self.assertEqual(updated["process_state"], "rejected")

    def test_api_approve_repeated_conflict(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_proposal(
            title="Already processed", content="Content", domain_id=domain["id"]
        )
        self.repository.approve_proposal(created["id"])
        with self.assertRaises(HTTPException) as ctx:
            approve_proposal(created["id"], self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_api_proposal_expired(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        # Crea una proposta già scaduta manipolando il DB direttamente
        created = self.repository.create_proposal(
            title="Expired", content="Content", domain_id=domain["id"]
        )
        now = _dt.datetime.now(_dt.timezone.utc)
        expired_at = (now - _dt.timedelta(hours=1)).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE knowledge_proposals SET expires_at = ? WHERE id = ?",
                (expired_at, created["id"]),
            )
            connection.commit()
        with self.assertRaises(HTTPException) as ctx:
            approve_proposal(created["id"], self.repository)
        self.assertEqual(ctx.exception.status_code, 409)

    # ---- Architecture / Isolation ----

    def test_api_m4_uses_knowledge_sqlite3(self) -> None:
        knowledge_path = default_knowledge_database_path()
        from app.memory.repository import default_memory_database_path

        memory_path = default_memory_database_path()
        self.assertNotEqual(str(knowledge_path), str(memory_path))
        self.assertEqual(knowledge_path.name, "knowledge.sqlite3")
        self.assertEqual(memory_path.name, "memories.sqlite3")

    def test_api_m4_db_is_temporary(self) -> None:
        self.assertEqual(
            self.repository.database_path, self.database_path
        )
        self.assertEqual(self.database_path.name, "knowledge.sqlite3")

    def test_api_archived_item_not_physically_deleted(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_item(
            title="Archive test", content="Content", domain_id=domain["id"]
        )
        # Soft delete
        archive_item(created["id"], self.repository)
        # Item still exists (archived)
        item = self.repository.get_item(created["id"])
        self.assertIsNotNone(item)
        self.assertEqual(item["item_state"], "archived")

    def test_api_audit_log_immutability(self) -> None:
        domain = self.repository.create_domain(name="Work", slug="work")
        created = self.repository.create_item(
            title="Audit", content="Content", domain_id=domain["id"]
        )
        audit = self.repository.audit_log(item_id=created["id"])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["action"], "knowledge.created")

        # Attempt to tamper via direct SQL should fail
        with sqlite3.connect(self.database_path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE knowledge_audit_log SET action = 'tampered' WHERE id = ?",
                    (audit[0]["id"],),
                )


if __name__ == "__main__":
    unittest.main()
