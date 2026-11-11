"""J.A.C.K. M4 Knowledge Engine repository.

SQLite-backed persistent knowledge store using a separate
``knowledge.sqlite3`` database, completely independent from M3's
``memories.sqlite3``.

Schema version: 1

Tables:
- knowledge_domains
- knowledge_items
- knowledge_versions
- knowledge_sources
- document_chunks
- knowledge_links
- knowledge_proposals
- knowledge_audit_log
- knowledge_settings
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Mapping

logger = logging.getLogger("jack.backend.memory")

SCHEMA_VERSION = 1
PROPOSAL_TTL = timedelta(hours=24)

KNOWLEDGE_TYPES = (
    "concept",
    "fact",
    "procedure",
    "definition",
    "theorem",
    "formula",
    "reference",
)

SOURCE_TYPES = (
    "document",
    "conversation",
    "import",
    "system",
    "autonomous",
)

ITEM_STATES = (
    "draft",
    "published",
    "archived",
)

VERIFICATION_STATUSES = (
    "unverified",
    "provisional",
    "verified",
    "inferred",
    "contradicted",
)

PROCESS_STATES = (
    "pending",
    "accepted",
    "rejected",
    "expired",
    "published",
)

RELATION_TYPES = (
    "related",
    "prerequisite",
    "contradicts",
    "supports",
    "updates",
    "instance_of",
    "part_of",
    "causes",
    "influences",
)

SYMMETRIC_RELATION_TYPES = ("related", "contradicts")


class KnowledgeNotFoundError(Exception):
    pass


class DuplicateMemoryLinkError(Exception):
    pass


class KnowledgeProposalConflictError(Exception):
    pass


def default_knowledge_database_path() -> Path:
    """Return the default path for the M4 knowledge database.

    Uses ``JACK_KNOWLEDGE_DB_PATH`` environment variable if set,
    otherwise the macOS Application Support directory for J.A.C.K.
    """
    override = os.getenv("JACK_KNOWLEDGE_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "J.A.C.K."
            / "knowledge.sqlite3"
        )
    return Path.home() / ".local" / "share" / "J.A.C.K." / "knowledge.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _domains_table_sql() -> str:
    return """
        CREATE TABLE IF NOT EXISTS knowledge_domains (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT,
            parent_domain_id TEXT REFERENCES knowledge_domains(id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """


def _knowledge_table_sql() -> str:
    return """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id TEXT PRIMARY KEY,
            domain_id TEXT NOT NULL REFERENCES knowledge_domains(id) ON DELETE RESTRICT,
            title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
            content TEXT NOT NULL CHECK(length(trim(content)) BETWEEN 1 AND 20000),
            summary TEXT,
            knowledge_type TEXT NOT NULL CHECK(knowledge_type IN (
                'concept', 'fact', 'procedure', 'definition', 'theorem', 'formula', 'reference'
            )),
            source_type TEXT NOT NULL CHECK(source_type IN (
                'document', 'conversation', 'import', 'system', 'autonomous'
            )),
            source_id TEXT,
            source_title TEXT,
            source_url TEXT,
            confidence_score REAL NOT NULL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            verification_status TEXT NOT NULL CHECK(verification_status IN (
                'unverified', 'provisional', 'verified', 'inferred', 'contradicted'
            )),
            item_state TEXT NOT NULL CHECK(item_state IN ('draft', 'published', 'archived')),
            version INTEGER NOT NULL DEFAULT 1,
            is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN (0, 1)),
            acquired_at TEXT NOT NULL,
            verified_at TEXT,
            verification_reason TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            importance INTEGER NOT NULL CHECK(importance BETWEEN 1 AND 5),
            excluded INTEGER NOT NULL DEFAULT 0 CHECK(excluded IN (0, 1)),
            conversation_id TEXT,
            last_used TEXT
        )
    """


def _versions_table_sql() -> str:
    return """
        CREATE TABLE knowledge_versions (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            change_reason TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        )
    """


def _sources_table_sql() -> str:
    return """
        CREATE TABLE knowledge_sources (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            document_type TEXT NOT NULL CHECK(document_type IN (
                'pdf', 'docx', 'txt', 'md', 'html', 'url', 'image'
            )),
            file_path TEXT,
            url TEXT,
            author TEXT,
            publisher TEXT,
            published_at TEXT,
            accessed_at TEXT,
            authority_score REAL CHECK(authority_score BETWEEN 0.0 AND 1.0),
            language TEXT,
            page_count INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """


def _chunks_table_sql() -> str:
    return """
        CREATE TABLE document_chunks (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
            item_id TEXT REFERENCES knowledge_items(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            page_number INTEGER,
            section_title TEXT,
            char_start INTEGER,
            char_end INTEGER,
            embedding_id TEXT,
            created_at TEXT NOT NULL
        )
    """


def _links_table_sql() -> str:
    return """
        CREATE TABLE knowledge_links (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            to_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            relation_type TEXT NOT NULL CHECK(relation_type IN (
                'related', 'prerequisite', 'contradicts', 'supports',
                'updates', 'instance_of', 'part_of', 'causes', 'influences'
            )),
            strength INTEGER NOT NULL CHECK(strength BETWEEN 1 AND 3),
            description TEXT,
            created_at TEXT NOT NULL,
            CHECK(from_id <> to_id)
        )
    """


def _proposals_table_sql() -> str:
    return """
        CREATE TABLE knowledge_proposals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            domain_id TEXT NOT NULL REFERENCES knowledge_domains(id) ON DELETE RESTRICT,
            payload_json TEXT NOT NULL,
            process_state TEXT NOT NULL CHECK(process_state IN (
                'pending', 'accepted', 'rejected', 'expired', 'published'
            )),
            verification_status TEXT NOT NULL CHECK(verification_status IN (
                'unverified', 'provisional', 'verified', 'inferred', 'contradicted'
            )),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            resolved_at TEXT,
            published_item_id TEXT UNIQUE REFERENCES knowledge_items(id) ON DELETE SET NULL
        )
    """


def _audit_table_sql() -> str:
    return """
        CREATE TABLE knowledge_audit_log (
            id TEXT PRIMARY KEY,
            item_id TEXT REFERENCES knowledge_items(id) ON DELETE RESTRICT,
            proposal_id TEXT REFERENCES knowledge_proposals(id) ON DELETE RESTRICT,
            action TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            details_json TEXT
        )
    """


def _settings_table_sql() -> str:
    return """
        CREATE TABLE knowledge_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """


class KnowledgeRepository:
    """Memory Engine repository with full CRUD, search, filters, relations,
    proposals, audit log, and approval flow.

    Uses a separate knowledge.sqlite3 database, independent from M3's
    memories.sqlite3.

    Schema version: 1
    """

    current_version: int = SCHEMA_VERSION

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser()

    def current_version(self) -> int:
        return SCHEMA_VERSION

    def initialize(self) -> None:
        """Initialize or migrate the knowledge database to schema version 1."""
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"The local knowledge database is newer than this app "
                    f"(v{version} > v{SCHEMA_VERSION})."
                )

            if version < SCHEMA_VERSION:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(_domains_table_sql())
                    connection.execute(_knowledge_table_sql())
                    connection.execute(_versions_table_sql())
                    connection.execute(_sources_table_sql())
                    connection.execute(_chunks_table_sql())
                    connection.execute(_links_table_sql())
                    connection.execute(_proposals_table_sql())
                    connection.execute(_audit_table_sql())
                    connection.execute(_settings_table_sql())
                    self._create_indexes(connection)
                    self._create_fts_table(connection)
                    self._create_fts_triggers(connection)
                    self._create_audit_triggers(connection)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            logger.info("Knowledge database running at schema v%d", SCHEMA_VERSION)

        self.database_path.chmod(0o600)

    def _create_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_domain "
            "ON knowledge_items(domain_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_type "
            "ON knowledge_items(knowledge_type)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_verification "
            "ON knowledge_items(verification_status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_state "
            "ON knowledge_items(item_state)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_source "
            "ON knowledge_items(source_type, source_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_items_updated "
            "ON knowledge_items(updated_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_versions_item "
            "ON knowledge_versions(item_id, version)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_source "
            "ON document_chunks(source_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_item "
            "ON document_chunks(item_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_links_from "
            "ON knowledge_links(from_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_links_to "
            "ON knowledge_links(to_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_audit_occurred "
            "ON knowledge_audit_log(occurred_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_proposals_state_expiry "
            "ON knowledge_proposals(process_state, expires_at)"
        )

    def _create_fts_table(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_items_fts
            USING fts5(
                title, content, summary,
                content=knowledge_items,
                content_rowid=rowid
            )
            """
        )

    def _create_fts_triggers(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_items_ai
            AFTER INSERT ON knowledge_items
            BEGIN
                INSERT INTO knowledge_items_fts(rowid, title, content, summary)
                VALUES (new.rowid, new.title, new.content, new.summary);
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_items_au
            AFTER UPDATE ON knowledge_items
            BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid, title, content, summary)
                VALUES ('delete', old.rowid, old.title, old.content, old.summary);
                INSERT INTO knowledge_items_fts(rowid, title, content, summary)
                VALUES (new.rowid, new.title, new.content, new.summary);
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_items_ad_delete
            AFTER DELETE ON knowledge_items
            BEGIN
                INSERT INTO knowledge_items_fts(knowledge_items_fts, rowid, title, content, summary)
                VALUES ('delete', old.rowid, old.title, old.content, old.summary);
            END
            """
        )

    def _create_audit_triggers(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_audit_no_update
            BEFORE UPDATE ON knowledge_audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Knowledge audit events are immutable.');
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_audit_no_delete
            BEFORE DELETE ON knowledge_audit_log
            BEGIN
                SELECT RAISE(ABORT, 'Knowledge audit events are immutable.');
            END
            """
        )

    def _backup_before_migration(self, connection: sqlite3.Connection) -> Path:
        backup_path = self.database_path.with_name(
            f"{self.database_path.name}.pre-v{SCHEMA_VERSION}.bak"
        )
        if not backup_path.exists():
            backup_connection = sqlite3.connect(backup_path, timeout=5)
            try:
                connection.backup(backup_connection)
                backup_connection.commit()
            finally:
                backup_connection.close()
        backup_path.chmod(0o600)
        return backup_path

    def _validate_current_schema(self, connection: sqlite3.Connection) -> None:
        tables = {
            str(row["name"])
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
        if not required_tables.issubset(tables):
            missing = required_tables - tables
            raise RuntimeError(
                f"The local knowledge database is incomplete. Missing tables: {sorted(missing)}"
            )

        required_item_columns = {
            "id",
            "domain_id",
            "title",
            "content",
            "summary",
            "knowledge_type",
            "source_type",
            "source_id",
            "source_title",
            "source_url",
            "confidence_score",
            "verification_status",
            "item_state",
            "version",
            "is_current",
            "acquired_at",
            "verified_at",
            "verification_reason",
            "expires_at",
            "created_at",
            "updated_at",
        }
        item_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(knowledge_items)").fetchall()
        }
        if not required_item_columns.issubset(item_columns):
            missing = required_item_columns - item_columns
            raise RuntimeError(
                f"The local knowledge database is incomplete. Missing items columns: {sorted(missing)}"
            )

        required_proposal_columns = {
            "id",
            "title",
            "content",
            "domain_id",
            "payload_json",
            "process_state",
            "verification_status",
            "created_at",
            "expires_at",
            "resolved_at",
            "published_item_id",
        }
        proposal_columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(knowledge_proposals)"
            ).fetchall()
        }
        if not required_proposal_columns.issubset(proposal_columns):
            missing = required_proposal_columns - proposal_columns
            raise RuntimeError(
                f"The local knowledge database is incomplete. Missing proposals columns: {sorted(missing)}"
            )

        required_audit_columns = {
            "id",
            "item_id",
            "proposal_id",
            "action",
            "occurred_at",
        }
        audit_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(knowledge_audit_log)").fetchall()
        }
        if not required_audit_columns.issubset(audit_columns):
            missing = required_audit_columns - audit_columns
            raise RuntimeError(
                f"The local knowledge database is incomplete. Missing audit columns: {sorted(missing)}"
            )

        audit_triggers = {
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'trigger' AND tbl_name = 'knowledge_audit_log'
                """
            ).fetchall()
        }
        if not {
            "knowledge_audit_no_update",
            "knowledge_audit_no_delete",
        }.issubset(audit_triggers):
            missing = {
                "knowledge_audit_no_update",
                "knowledge_audit_no_delete",
            } - audit_triggers
            raise RuntimeError(
                f"The local knowledge database is incomplete. Missing audit triggers: {sorted(missing)}"
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ---- CRUD: Domains ----

    def create_domain(
        self,
        *,
        name: str,
        slug: str,
        description: str | None = None,
        parent_domain_id: str | None = None,
    ) -> dict[str, object]:
        now = _now()
        domain_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_domains
                (id, name, slug, description, parent_domain_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    domain_id,
                    name,
                    slug,
                    description,
                    parent_domain_id,
                    now,
                    now,
                ),
            )
        return {
            "id": domain_id,
            "name": name,
            "slug": slug,
            "description": description,
            "parent_domain_id": parent_domain_id,
            "created_at": now,
            "updated_at": now,
        }

    def get_domain(self, domain_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_domains WHERE id = ?", (domain_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_domains(
        self,
        *,
        parent_domain_id: str | None = None,
    ) -> list[dict[str, object]]:
        with self._connection() as connection:
            if parent_domain_id is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_domains
                    WHERE parent_domain_id = ?
                    ORDER BY created_at DESC, id ASC
                    """,
                    (parent_domain_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_domains
                    ORDER BY created_at DESC, id ASC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def update_domain(
        self,
        domain_id: str,
        *,
        name: str | None = None,
        slug: str | None = None,
        description: str | None = None,
        parent_domain_id: str | None = None,
    ) -> dict[str, object] | None:
        existing = self.get_domain(domain_id)
        if existing is None:
            return None
        now = _now()
        values: dict[str, object] = {}
        if name is not None:
            values["name"] = name
        if slug is not None:
            values["slug"] = slug
        if description is not None:
            values["description"] = description
        if parent_domain_id is not None:
            values["parent_domain_id"] = parent_domain_id
        if not values:
            return existing
        values["updated_at"] = now
        values["id"] = domain_id
        with self._connection() as connection:
            set_clause = ", ".join(f"{k} = :{k}" for k in values if k != "id")
            connection.execute(
                f"""
                UPDATE knowledge_domains
                SET {set_clause}
                WHERE id = :id
                """,
                values,
            )
        return self.get_domain(domain_id)

    def delete_domain(self, domain_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM knowledge_domains WHERE id = ?", (domain_id,)
            )
        return cursor.rowcount > 0

    # ---- CRUD: Items ----

    def create_item(
        self,
        *,
        title: str,
        content: str,
        domain_id: str,
        knowledge_type: str = "concept",
        source_type: str = "system",
        source_id: str | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
        confidence_score: float = 1.0,
        verification_status: str = "unverified",
        item_state: str = "draft",
        acquired_at: str | None = None,
        verified_at: str | None = None,
        verification_reason: str | None = None,
        expires_at: str | None = None,
        tags: list[str] | None = None,
        importance: int = 3,
        excluded: bool = False,
        conversation_id: str | None = None,
        last_used: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        if knowledge_type not in KNOWLEDGE_TYPES:
            raise ValueError(f"Unknown knowledge type: {knowledge_type}")
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Unknown source type: {source_type}")
        if item_state not in ITEM_STATES:
            raise ValueError(f"Invalid item state: {item_state}")
        if verification_status not in VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status: {verification_status}")
        if not 1 <= importance <= 5:
            raise ValueError("importance must be between 1 and 5")
        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")

        domain = self.get_domain(domain_id)
        if domain is None:
            raise KnowledgeNotFoundError(f"Domain {domain_id} not found")

        now = _now()
        if created_at is None:
            created_at = now
        if acquired_at is None:
            acquired_at = created_at

        item_id = str(uuid.uuid4())
        item: dict[str, object] = {
            "id": item_id,
            "domain_id": domain_id,
            "title": title,
            "content": content,
            "summary": None,
            "knowledge_type": knowledge_type,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "source_url": source_url,
            "confidence_score": confidence_score,
            "verification_status": verification_status,
            "item_state": item_state,
            "version": 1,
            "is_current": 1,
            "acquired_at": acquired_at,
            "verified_at": verified_at,
            "verification_reason": verification_reason,
            "expires_at": expires_at,
            "created_at": created_at,
            "updated_at": created_at,
            "tags": tags or [],
            "importance": importance,
            "excluded": excluded,
            "conversation_id": conversation_id,
            "last_used": last_used,
        }
        stored = self._encode_item(item)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_items (
                    id, domain_id, title, content, summary, knowledge_type,
                    source_type, source_id, source_title, source_url,
                    confidence_score, verification_status, item_state,
                    version, is_current, acquired_at, verified_at,
                    verification_reason, expires_at, created_at, updated_at,
                    tags, importance, excluded, conversation_id, last_used
                ) VALUES (
                    :id, :domain_id, :title, :content, :summary, :knowledge_type,
                    :source_type, :source_id, :source_title, :source_url,
                    :confidence_score, :verification_status, :item_state,
                    :version, :is_current, :acquired_at, :verified_at,
                    :verification_reason, :expires_at, :created_at, :updated_at,
                    :tags, :importance, :excluded, :conversation_id, :last_used
                )
                """,
                stored,
            )
            self._append_audit(
                connection,
                item_id=item_id,
                action="knowledge.created",
            )
        return self._decode_item(stored)

    def get_item(self, item_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_items WHERE id = ?", (item_id,)
            ).fetchone()
        return self._decode_item(dict(row)) if row is not None else None

    def update_item(
        self,
        item_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        knowledge_type: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
        confidence_score: float | None = None,
        verification_status: str | None = None,
        item_state: str | None = None,
        verification_reason: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, object] | None:
        existing = self.get_item(item_id)
        if existing is None:
            return None

        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_versions (
                    id, item_id, version, content, summary,
                    change_reason, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    item_id,
                    existing["version"],
                    existing["content"],
                    existing["summary"],
                    "versioned_update",
                    now,
                    "system",
                ),
            )

            update_fields: dict[str, object] = {}
            if title is not None:
                update_fields["title"] = title
            if content is not None:
                update_fields["content"] = content
            if summary is not None:
                update_fields["summary"] = summary
            if knowledge_type is not None:
                update_fields["knowledge_type"] = knowledge_type
            if source_type is not None:
                update_fields["source_type"] = source_type
            if source_id is not None:
                update_fields["source_id"] = source_id
            if source_title is not None:
                update_fields["source_title"] = source_title
            if source_url is not None:
                update_fields["source_url"] = source_url
            if confidence_score is not None:
                update_fields["confidence_score"] = confidence_score
            if verification_status is not None:
                update_fields["verification_status"] = verification_status
            if item_state is not None:
                update_fields["item_state"] = item_state
            if verification_reason is not None:
                update_fields["verification_reason"] = verification_reason
            if expires_at is not None:
                update_fields["expires_at"] = expires_at

            if not update_fields:
                return existing

            update_fields["version"] = existing["version"] + 1
            update_fields["updated_at"] = now
            update_fields["id"] = item_id

            set_clause = ", ".join(f"{k} = :{k}" for k in update_fields if k != "id")
            connection.execute(
                f"""
                UPDATE knowledge_items
                SET {set_clause}
                WHERE id = :id
                """,
                update_fields,
            )
            self._append_audit(
                connection,
                item_id=item_id,
                action="knowledge.updated",
            )
        return self.get_item(item_id)

    def delete_item(self, item_id: str) -> bool:
        """Archive a knowledge item (soft delete)."""
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE knowledge_items SET item_state = 'archived', updated_at = ? WHERE id = ?",
                (_now(), item_id),
            )
            if cursor.rowcount:
                self._append_audit(
                    connection,
                    item_id=item_id,
                    action="knowledge.archived",
                )
            return cursor.rowcount > 0

    def list_items(
        self,
        *,
        domain_id: str | None = None,
        knowledge_type: str | None = None,
        source_type: str | None = None,
        verification_status: str | None = None,
        item_state: str | None = None,
        is_current: bool | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        conditions: list[str] = []
        params: list[object] = []
        if domain_id is not None:
            conditions.append("domain_id = ?")
            params.append(domain_id)
        if knowledge_type is not None:
            conditions.append("knowledge_type = ?")
            params.append(knowledge_type)
        if source_type is not None:
            conditions.append("source_type = ?")
            params.append(source_type)
        if verification_status is not None:
            conditions.append("verification_status = ?")
            params.append(verification_status)
        if item_state is not None:
            conditions.append("item_state = ?")
            params.append(item_state)
        if is_current is not None:
            conditions.append("is_current = ?")
            params.append(1 if is_current else 0)
        if query:
            conditions.append("(title LIKE ? OR content LIKE ? OR summary LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like])

        where_clause = " AND ".join(conditions) if conditions else "1"
        params.extend([limit, offset])

        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM knowledge_items
                WHERE {where_clause}
                ORDER BY updated_at DESC, created_at DESC, id ASC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return [self._decode_item(dict(row)) for row in rows]

    def search_items(
        self,
        query: str,
        *,
        domain_id: str | None = None,
        knowledge_type: str | None = None,
        verification_status: str | None = None,
        item_state: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        with self._connection() as connection:
            fts_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_items_fts'"
            ).fetchone() is not None

            if fts_exists and query:
                rows = connection.execute(
                    """
                    SELECT ki.* FROM knowledge_items ki
                    INNER JOIN knowledge_items_fts fts ON ki.rowid = fts.rowid
                    WHERE knowledge_items_fts MATCH ?
                    ORDER BY ki.updated_at DESC, ki.created_at DESC, ki.id ASC
                    LIMIT ? OFFSET ?
                    """,
                    (query, limit, 0),
                ).fetchall()
            else:
                like = f"%{query}%"
                conditions = ["(title LIKE ? OR content LIKE ? OR summary LIKE ?)"]
                params = [like, like, like]
                if domain_id is not None:
                    conditions.append("domain_id = ?")
                    params.append(domain_id)
                if knowledge_type is not None:
                    conditions.append("knowledge_type = ?")
                    params.append(knowledge_type)
                if verification_status is not None:
                    conditions.append("verification_status = ?")
                    params.append(verification_status)
                if item_state is not None:
                    conditions.append("item_state = ?")
                    params.append(item_state)
                where_clause = " AND ".join(conditions) if conditions else "1"
                params.extend([limit, 0])
                rows = connection.execute(
                    f"""
                    SELECT * FROM knowledge_items
                    WHERE {where_clause}
                    ORDER BY updated_at DESC, created_at DESC, id ASC
                    LIMIT ? OFFSET ?
                    """,
                    params,
                ).fetchall()
        return [self._decode_item(dict(row)) for row in rows]

    # ---- Relations ----

    def create_link(
        self,
        *,
        from_id: str,
        to_id: str,
        relation_type: str,
        strength: int = 1,
        description: str | None = None,
    ) -> dict[str, object]:
        if from_id == to_id:
            raise ValueError("from_id and to_id must be different")
        if not 1 <= strength <= 3:
            raise ValueError("strength must be between 1 and 3")
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"Invalid relation type: {relation_type}")

        from_item = self.get_item(from_id)
        to_item = self.get_item(to_id)
        if from_item is None or to_item is None:
            raise KnowledgeNotFoundError("Source or target item not found")

        link_id = str(uuid.uuid4())
        now = _now()
        relation_key = relation_type.strip().casefold()

        with self._connection() as connection:
            if relation_type in SYMMETRIC_RELATION_TYPES:
                existing = connection.execute(
                    """
                    SELECT id FROM knowledge_links
                    WHERE relation_type = ? AND strength = ?
                    AND (
                        (from_id = ? AND to_id = ?)
                        OR (from_id = ? AND to_id = ?)
                    )
                    """,
                    (relation_type, strength, from_id, to_id, to_id, from_id),
                ).fetchone()
            else:
                existing = connection.execute(
                    """
                    SELECT id FROM knowledge_links
                    WHERE relation_type = ? AND strength = ?
                    AND from_id = ? AND to_id = ?
                    """,
                    (relation_type, strength, from_id, to_id),
                ).fetchone()

            if existing:
                raise DuplicateMemoryLinkError(
                    f"Link {relation_type} from {from_id} to {to_id} already exists"
                )

            connection.execute(
                """
                INSERT INTO knowledge_links
                (id, from_id, to_id, relation_type, strength, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link_id,
                    from_id,
                    to_id,
                    relation_type,
                    strength,
                    description,
                    now,
                ),
            )
            self._append_audit(
                connection,
                item_id=from_id,
                action="knowledge.link.created",
            )
        return {
            "id": link_id,
            "from_id": from_id,
            "to_id": to_id,
            "relation_type": relation_type,
            "relation_key": relation_key,
            "strength": strength,
            "description": description,
            "created_at": now,
        }

    def get_link(self, link_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_links WHERE id = ?", (link_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_links(
        self,
        *,
        item_id: str | None = None,
        relation_type: str | None = None,
    ) -> list[dict[str, object]]:
        with self._connection() as connection:
            if item_id is not None and relation_type is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_links
                    WHERE (from_id = ? OR to_id = ?) AND relation_type = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (item_id, item_id, relation_type),
                ).fetchall()
            elif item_id is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_links
                    WHERE from_id = ? OR to_id = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (item_id, item_id),
                ).fetchall()
            elif relation_type is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_links
                    WHERE relation_type = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (relation_type,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_links
                    ORDER BY created_at ASC, id ASC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def delete_link(self, link_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM knowledge_links WHERE id = ?", (link_id,)
            )
            if cursor.rowcount:
                self._append_audit(
                    connection,
                    action="knowledge.link.deleted",
                )
            return cursor.rowcount > 0

    # ---- Proposals ----

    def create_proposal(
        self,
        *,
        title: str,
        content: str,
        domain_id: str,
        knowledge_type: str = "concept",
        source_type: str = "autonomous",
        source_id: str | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
        confidence_score: float = 1.0,
        verification_status: str = "unverified",
        tags: list[str] | None = None,
        importance: int = 3,
        excluded: bool = False,
        conversation_id: str | None = None,
    ) -> dict[str, object]:
        if knowledge_type not in KNOWLEDGE_TYPES:
            raise ValueError(f"Unknown knowledge type: {knowledge_type}")
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Unknown source type: {source_type}")
        if verification_status not in VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification status: {verification_status}")
        if not 1 <= importance <= 5:
            raise ValueError("importance must be between 1 and 5")
        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")

        domain = self.get_domain(domain_id)
        if domain is None:
            raise KnowledgeNotFoundError(f"Domain {domain_id} not found")

        now = datetime.now(timezone.utc)
        proposal_id = str(uuid.uuid4())
        created_at = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        expires_at = (now + PROPOSAL_TTL).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )

        payload = {
            "title": title,
            "content": content,
            "domain_id": domain_id,
            "knowledge_type": knowledge_type,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "source_url": source_url,
            "confidence_score": confidence_score,
            "verification_status": verification_status,
            "tags": tags or [],
            "importance": importance,
            "excluded": excluded,
            "conversation_id": conversation_id,
        }

        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_proposals
                (id, title, content, domain_id, payload_json,
                 process_state, verification_status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (
                    proposal_id,
                    title,
                    content,
                    domain_id,
                    json.dumps(payload, ensure_ascii=False),
                    verification_status,
                    created_at,
                    expires_at,
                ),
            )
            self._append_audit(
                connection,
                proposal_id=proposal_id,
                action="proposal.created",
            )
        return self._proposal_result(
            proposal_id,
            payload,
            "pending",
            created_at,
            expires_at,
        )

    def list_proposals(
        self,
        *,
        process_state: str | None = None,
    ) -> list[dict[str, object]]:
        with self._connection() as connection:
            self._expire_pending_proposals(connection)
            if process_state is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_proposals
                    WHERE process_state = ?
                    ORDER BY created_at DESC, id ASC
                    """,
                    (process_state,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_proposals
                    ORDER BY created_at DESC, id ASC
                    """
                ).fetchall()
        return [self._decode_proposal(dict(row)) for row in rows]

    def get_proposal(self, proposal_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            self._expire_pending_proposals(connection, proposal_id=proposal_id)
            row = connection.execute(
                "SELECT * FROM knowledge_proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
        return self._decode_proposal(dict(row)) if row is not None else None

    def approve_proposal(self, proposal_id: str) -> dict[str, object] | None:
        expired = False
        item: dict[str, object] | None = None
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM knowledge_proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                return None
            proposal = self._decode_proposal(dict(row))
            if proposal["process_state"] != "pending":
                raise KnowledgeProposalConflictError(str(proposal["process_state"]))
            if str(proposal["expires_at"]) <= _now():
                connection.execute(
                    """
                    UPDATE knowledge_proposals
                    SET process_state = 'expired', resolved_at = ?
                    WHERE id = ? AND process_state = 'pending'
                    """,
                    (_now(), proposal_id),
                )
                self._append_audit(
                    connection,
                    proposal_id=proposal_id,
                    action="proposal.expired",
                )
                expired = True
                raise KnowledgeProposalConflictError("expired")
            else:
                payload = json.loads(str(row["payload_json"]))
                now = _now()
                item = self._create_item_internal(
                    connection,
                    title=payload["title"],
                    content=payload["content"],
                    domain_id=payload["domain_id"],
                    knowledge_type=payload.get("knowledge_type", "concept"),
                    source_type=payload.get("source_type", "autonomous"),
                    source_id=payload.get("source_id"),
                    source_title=payload.get("source_title"),
                    source_url=payload.get("source_url"),
                    confidence_score=payload.get("confidence_score", 1.0),
                    verification_status=payload.get("verification_status", "unverified"),
                    item_state="published",
                    tags=payload.get("tags", []),
                    importance=payload.get("importance", 3),
                    excluded=payload.get("excluded", False),
                    conversation_id=payload.get("conversation_id"),
                    created_at=now,
                )
                connection.execute(
                    """
                    UPDATE knowledge_proposals
                    SET process_state = 'published', resolved_at = ?, published_item_id = ?
                    WHERE id = ? AND process_state = 'pending'
                    """,
                    (now, item["id"], proposal_id),
                )
                self._append_audit(
                    connection,
                    item_id=item["id"],
                    proposal_id=proposal_id,
                    action="proposal.approved",
                )
        if expired:
            raise KnowledgeProposalConflictError("expired")
        return item

    def reject_proposal(self, proposal_id: str) -> dict[str, object] | None:
        expired = False
        result: dict[str, object] | None = None
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM knowledge_proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                return None
            proposal = self._decode_proposal(dict(row))
            if proposal["process_state"] != "pending":
                raise KnowledgeProposalConflictError(str(proposal["process_state"]))
            if str(proposal["expires_at"]) <= _now():
                connection.execute(
                    """
                    UPDATE knowledge_proposals
                    SET process_state = 'expired', resolved_at = ?
                    WHERE id = ? AND process_state = 'pending'
                    """,
                    (_now(), proposal_id),
                )
                self._append_audit(
                    connection,
                    proposal_id=proposal_id,
                    action="proposal.expired",
                )
                expired = True
                raise KnowledgeProposalConflictError("expired")
            else:
                now = _now()
                connection.execute(
                    """
                    UPDATE knowledge_proposals
                    SET process_state = 'rejected', resolved_at = ?
                    WHERE id = ? AND process_state = 'pending'
                    """,
                    (now, proposal_id),
                )
                self._append_audit(
                    connection,
                    proposal_id=proposal_id,
                    action="proposal.rejected",
                )
                result = self._proposal_result(
                    proposal_id,
                    json.loads(str(row["payload_json"])),
                    "rejected",
                    str(row["created_at"]),
                    str(row["expires_at"]),
                    resolved_at=now,
                )
        if expired:
            raise KnowledgeProposalConflictError("expired")
        return result

    def _expire_pending_proposals(
        self,
        connection: sqlite3.Connection,
        *,
        proposal_id: str | None = None,
    ) -> None:
        now = _now()
        if proposal_id is None:
            rows = connection.execute(
                """
                SELECT id FROM knowledge_proposals
                WHERE process_state = 'pending' AND expires_at <= ?
                """,
                (now,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id FROM knowledge_proposals
                WHERE id = ? AND process_state = 'pending' AND expires_at <= ?
                """,
                (proposal_id, now),
            ).fetchall()
        for row in rows:
            current_id = str(row["id"])
            connection.execute(
                """
                UPDATE knowledge_proposals
                SET process_state = 'expired', resolved_at = ?
                WHERE id = ? AND process_state = 'pending'
                """,
                (now, current_id),
            )
            self._append_audit(
                connection,
                proposal_id=current_id,
                action="proposal.expired",
            )

    def _create_item_internal(
        self,
        connection: sqlite3.Connection,
        *,
        title: str,
        content: str,
        domain_id: str,
        knowledge_type: str = "concept",
        source_type: str = "system",
        source_id: str | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
        confidence_score: float = 1.0,
        verification_status: str = "unverified",
        item_state: str = "draft",
        tags: list[str] | None = None,
        importance: int = 3,
        excluded: bool = False,
        conversation_id: str | None = None,
        last_used: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        if created_at is None:
            created_at = _now()
        item_id = str(uuid.uuid4())
        item: dict[str, object] = {
            "id": item_id,
            "domain_id": domain_id,
            "title": title,
            "content": content,
            "summary": None,
            "knowledge_type": knowledge_type,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "source_url": source_url,
            "confidence_score": confidence_score,
            "verification_status": verification_status,
            "item_state": item_state,
            "version": 1,
            "is_current": 1,
            "acquired_at": created_at,
            "verified_at": None,
            "verification_reason": None,
            "expires_at": None,
            "created_at": created_at,
            "updated_at": created_at,
            "tags": tags or [],
            "importance": importance,
            "excluded": excluded,
            "conversation_id": conversation_id,
            "last_used": last_used,
        }
        stored = self._encode_item(item)
        if stored.get("created_at") is None:
            stored["created_at"] = _now()
        connection.execute(
            """
            INSERT INTO knowledge_items (
                id, domain_id, title, content, summary, knowledge_type,
                source_type, source_id, source_title, source_url,
                confidence_score, verification_status, item_state,
                version, is_current, acquired_at, verified_at,
                verification_reason, expires_at, created_at, updated_at,
                tags, importance, excluded, conversation_id, last_used
            ) VALUES (
                :id, :domain_id, :title, :content, :summary, :knowledge_type,
                :source_type, :source_id, :source_title, :source_url,
                :confidence_score, :verification_status, :item_state,
                :version, :is_current, :acquired_at, :verified_at,
                :verification_reason, :expires_at, :created_at, :updated_at,
                :tags, :importance, :excluded, :conversation_id, :last_used
            )
            """,
            stored,
        )
        return item

    # ---- Audit Log ----

    def audit_log(
        self,
        *,
        item_id: str | None = None,
        proposal_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        conditions: list[str] = []
        params: list[object] = []
        if item_id is not None:
            conditions.append("item_id = ?")
            params.append(item_id)
        if proposal_id is not None:
            conditions.append("proposal_id = ?")
            params.append(proposal_id)
        if action is not None:
            conditions.append("action = ?")
            params.append(action)
        where_clause = " AND ".join(conditions) if conditions else "1"
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, item_id, proposal_id, action, occurred_at, details_json
                FROM knowledge_audit_log
                WHERE {where_clause}
                ORDER BY occurred_at DESC, id DESC LIMIT ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        *,
        action: str,
        item_id: str | None = None,
        proposal_id: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO knowledge_audit_log
            (id, item_id, proposal_id, action, occurred_at, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                item_id,
                proposal_id,
                action,
                _now(),
                None,
            ),
        )

    # ---- Encoding / Decoding ----

    @staticmethod
    def _encode_item(item: Mapping[str, object]) -> dict[str, object]:
        stored = dict(item)
        if "tags" in stored and stored["tags"] is not None:
            stored["tags"] = json.dumps(stored["tags"], ensure_ascii=False)
        if "excluded" in stored:
            stored["excluded"] = int(bool(stored["excluded"]))
        return stored

    @classmethod
    def _decode_item(cls, row: Mapping[str, object]) -> dict[str, object]:
        item = dict(row)
        try:
            tags = json.loads(str(item["tags"])) if item.get("tags") else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            tags = []
        item["tags"] = tags
        item["importance"] = int(item["importance"]) if item.get("importance") is not None else 3
        item["excluded"] = bool(item["excluded"]) if item.get("excluded") is not None else False
        item["confidence_score"] = (
            float(item["confidence_score"])
            if item.get("confidence_score") is not None
            else 1.0
        )
        item["version"] = int(item["version"]) if item.get("version") is not None else 1
        item["is_current"] = bool(item["is_current"]) if item.get("is_current") is not None else True
        return item

    @classmethod
    def _proposal_result(
        cls,
        proposal_id: str,
        payload: Mapping[str, object],
        process_state: str,
        created_at: str,
        expires_at: str,
        *,
        resolved_at: str | None = None,
        published_item_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "id": proposal_id,
            "title": payload["title"],
            "content": payload["content"],
            "domain_id": payload["domain_id"],
            "knowledge_type": payload.get("knowledge_type", "concept"),
            "source_type": payload.get("source_type", "autonomous"),
            "source_id": payload.get("source_id"),
            "source_title": payload.get("source_title"),
            "source_url": payload.get("source_url"),
            "confidence_score": payload.get("confidence_score", 1.0),
            "verification_status": payload.get("verification_status", "unverified"),
            "tags": payload.get("tags", []),
            "importance": payload.get("importance", 3),
            "excluded": payload.get("excluded", False),
            "conversation_id": payload.get("conversation_id"),
            "process_state": process_state,
            "created_at": created_at,
            "expires_at": expires_at,
            "resolved_at": resolved_at,
            "published_item_id": published_item_id,
        }

    @classmethod
    def _decode_proposal(cls, row: Mapping[str, object]) -> dict[str, object]:
        try:
            payload = json.loads(str(row["payload_json"]))
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("Stored knowledge proposal is invalid.") from error
        if not isinstance(payload, dict):
            raise RuntimeError("Stored knowledge proposal is invalid.")
        return cls._proposal_result(
            str(row["id"]),
            payload,
            str(row["process_state"]),
            str(row["created_at"]),
            str(row["expires_at"]),
            resolved_at=str(row["resolved_at"]) if row["resolved_at"] is not None else None,
            published_item_id=str(row["published_item_id"]) if row["published_item_id"] is not None else None,
        )
