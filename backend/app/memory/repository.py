from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping

logger = logging.getLogger("jack.backend.memory")


SCHEMA_VERSION = 2
MEMORY_CATEGORIES = (
    "identity",
    "work",
    "projects",
    "people",
    "technical",
    "preferences",
    "events",
    "other",
)
LEGACY_CATEGORY_MAP = {
    "personale": "identity",
    "lavoro": "work",
    "progetti": "projects",
    "preferenze": "preferences",
    "note": "other",
}
_MEMORY_METADATA_FIELDS = {
    "source_type",
    "source",
    "verification",
    "tags",
    "importance",
    "excluded",
    "conversation_id",
}


class MemoryNotFoundError(Exception):
    pass


class DuplicateMemoryLinkError(Exception):
    pass


def default_memory_database_path() -> Path:
    override = os.getenv("JACK_MEMORY_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "J.A.C.K."
            / "memories.sqlite3"
        )

    return Path.home() / ".local" / "share" / "J.A.C.K." / "memories.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _memory_table_sql(table_name: str = "memories") -> str:
    return f"""
        CREATE TABLE {table_name} (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
            content TEXT NOT NULL CHECK(length(trim(content)) BETWEEN 1 AND 20000),
            category TEXT NOT NULL CHECK(category IN (
                'identity', 'work', 'projects', 'people',
                'technical', 'preferences', 'events', 'other'
            )),
            source_type TEXT NOT NULL CHECK(source_type IN (
                'saved', 'retrieved', 'inference'
            )),
            source TEXT,
            verification TEXT NOT NULL CHECK(verification IN (
                'verified', 'to_verify', 'inferred'
            )),
            tags TEXT NOT NULL DEFAULT '[]',
            importance INTEGER NOT NULL CHECK(importance BETWEEN 1 AND 5),
            excluded INTEGER NOT NULL DEFAULT 0 CHECK(excluded IN (0, 1)),
            conversation_id TEXT,
            last_used TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """


class MemoryRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError("The local memory database is newer than this app.")

            has_memories = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'memories'"
            ).fetchone() is not None
            if version == SCHEMA_VERSION:
                self._validate_current_schema(connection)
            else:
                if has_memories:
                    self._backup_before_migration(connection)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    if has_memories:
                        migrated_count = self._migrate_legacy_memories(connection)
                    else:
                        migrated_count = 0
                        connection.execute(_memory_table_sql())
                    self._create_link_table(connection)
                    self._create_indexes(connection)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                if has_memories:
                    logger.info(
                        "Migrated %d memory record(s) to schema version %d",
                        migrated_count,
                        SCHEMA_VERSION,
                    )

        self.database_path.chmod(0o600)

    def list(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        excluded: bool | None = None,
    ) -> list[dict[str, object]]:
        clauses: list[str] = []
        parameters: list[object] = []
        if category is not None:
            clauses.append("category = ?")
            parameters.append(category)
        if excluded is not None:
            clauses.append("excluded = ?")
            parameters.append(int(excluded))

        sql = "SELECT * FROM memories"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, created_at DESC, id ASC"

        with self._connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        memories = [self._decode_memory_row(row) for row in rows]
        if query is None or not query.strip():
            return memories

        normalized_query = query.casefold().strip()
        return [
            memory
            for memory in memories
            if normalized_query
            in f"{memory['title']}\n{memory['content']}".casefold()
        ]

    def get(self, memory_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return self._decode_memory_row(row) if row is not None else None

    def create(
        self,
        *,
        title: str,
        content: str,
        category: str,
        metadata: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        now = _now()
        memory: dict[str, object] = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "category": category,
            "source_type": "saved",
            "source": "user_entry",
            "verification": "to_verify",
            "tags": [],
            "importance": 3,
            "excluded": False,
            "conversation_id": None,
            "last_used": None,
            "created_at": now,
            "updated_at": now,
        }
        memory.update(self._clean_metadata(metadata))
        stored = self._encode_memory(memory)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id, title, content, category, source_type, source,
                    verification, tags, importance, excluded, conversation_id,
                    last_used, created_at, updated_at
                ) VALUES (
                    :id, :title, :content, :category, :source_type, :source,
                    :verification, :tags, :importance, :excluded, :conversation_id,
                    :last_used, :created_at, :updated_at
                )
                """,
                stored,
            )
        return memory

    def update(
        self,
        memory_id: str,
        *,
        title: str,
        content: str,
        category: str,
        metadata: Mapping[str, object] | None = None,
    ) -> dict[str, object] | None:
        values: dict[str, object] = {
            "title": title,
            "content": content,
            "category": category,
            "updated_at": _now(),
        }
        values.update(self._encode_metadata(self._clean_metadata(metadata)))
        assignments = ", ".join(f"{field} = :{field}" for field in values)
        values["id"] = memory_id
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {assignments} WHERE id = :id",
                values,
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return self._decode_memory_row(row) if row is not None else None

    def set_excluded(self, memory_id: str, excluded: bool) -> dict[str, object] | None:
        return self._update_memory_field(memory_id, "excluded", int(excluded))

    def mark_used(self, memory_id: str) -> dict[str, object] | None:
        now = _now()
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE memories SET last_used = ?, updated_at = ? WHERE id = ?",
                (now, now, memory_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return self._decode_memory_row(row) if row is not None else None

    def delete(self, memory_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,),
            )
        return cursor.rowcount > 0

    def graph(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        excluded: bool | None = None,
    ) -> dict[str, list[dict[str, object]]]:
        nodes = self.list(query=query, category=category, excluded=excluded)
        node_ids = {str(node["id"]) for node in nodes}
        edges = [
            edge
            for edge in self.list_links()
            if edge["from_id"] in node_ids and edge["to_id"] in node_ids
        ]
        return {"nodes": nodes, "edges": edges}

    def list_links(self, *, memory_id: str | None = None) -> list[dict[str, object]]:
        sql = (
            "SELECT id, from_id, to_id, relation, strength, created_at "
            "FROM memory_links"
        )
        parameters: tuple[str, ...] = ()
        if memory_id is not None:
            sql += " WHERE from_id = ? OR to_id = ?"
            parameters = (memory_id, memory_id)
        sql += " ORDER BY created_at ASC, id ASC"
        with self._connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    def get_link(self, link_id: str) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, from_id, to_id, relation, strength, created_at "
                "FROM memory_links WHERE id = ?",
                (link_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def create_link(
        self,
        *,
        from_id: str,
        to_id: str,
        relation: str,
        strength: int,
    ) -> dict[str, object]:
        link = {
            "id": str(uuid.uuid4()),
            "from_id": from_id,
            "to_id": to_id,
            "relation": relation,
            "strength": strength,
            "created_at": _now(),
        }
        with self._connection() as connection:
            self._require_memories(connection, from_id, to_id)
            try:
                connection.execute(
                    """
                    INSERT INTO memory_links
                    (id, from_id, to_id, relation, relation_key, strength, created_at)
                    VALUES (
                        :id, :from_id, :to_id, :relation, :relation_key,
                        :strength, :created_at
                    )
                    """,
                    {**link, "relation_key": relation.strip().casefold()},
                )
            except sqlite3.IntegrityError as error:
                if "idx_memory_links_equivalent" in str(error):
                    raise DuplicateMemoryLinkError from error
                raise MemoryNotFoundError from error
        return link

    def update_link(
        self,
        link_id: str,
        *,
        from_id: str,
        to_id: str,
        relation: str,
        strength: int,
    ) -> dict[str, object] | None:
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT created_at FROM memory_links WHERE id = ?",
                (link_id,),
            ).fetchone()
            if existing is None:
                return None
            self._require_memories(connection, from_id, to_id)
            try:
                connection.execute(
                    """
                    UPDATE memory_links
                    SET from_id = ?, to_id = ?, relation = ?, relation_key = ?, strength = ?
                    WHERE id = ?
                    """,
                    (
                        from_id,
                        to_id,
                        relation,
                        relation.strip().casefold(),
                        strength,
                        link_id,
                    ),
                )
            except sqlite3.IntegrityError as error:
                if "idx_memory_links_equivalent" in str(error):
                    raise DuplicateMemoryLinkError from error
                raise MemoryNotFoundError from error
            row = connection.execute(
                "SELECT id, from_id, to_id, relation, strength, created_at "
                "FROM memory_links WHERE id = ?",
                (link_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def delete_link(self, link_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memory_links WHERE id = ?",
                (link_id,),
            )
        return cursor.rowcount > 0

    def _update_memory_field(
        self,
        memory_id: str,
        field: str,
        value: object,
    ) -> dict[str, object] | None:
        now = _now()
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE memories SET {field} = ?, updated_at = ? WHERE id = ?",
                (value, now, memory_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return self._decode_memory_row(row) if row is not None else None

    @staticmethod
    def _require_memories(
        connection: sqlite3.Connection,
        from_id: str,
        to_id: str,
    ) -> None:
        rows = connection.execute(
            "SELECT id FROM memories WHERE id IN (?, ?)",
            (from_id, to_id),
        ).fetchall()
        if len(rows) != 2:
            raise MemoryNotFoundError

    @staticmethod
    def _clean_metadata(
        metadata: Mapping[str, object] | None,
    ) -> dict[str, object]:
        if metadata is None:
            return {}
        return {
            key: value
            for key, value in metadata.items()
            if key in _MEMORY_METADATA_FIELDS
        }

    @staticmethod
    def _encode_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
        values = dict(metadata)
        if "tags" in values:
            values["tags"] = json.dumps(values["tags"], ensure_ascii=False)
        if "excluded" in values:
            values["excluded"] = int(bool(values["excluded"]))
        return values

    @classmethod
    def _encode_memory(cls, memory: Mapping[str, object]) -> dict[str, object]:
        stored = dict(memory)
        stored.update(cls._encode_metadata(stored))
        stored["excluded"] = int(bool(stored["excluded"]))
        return stored

    @staticmethod
    def _decode_memory_row(row: sqlite3.Row) -> dict[str, object]:
        memory = dict(row)
        try:
            tags = json.loads(str(memory["tags"]))
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("Stored memory tags are invalid.") from error
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise RuntimeError("Stored memory tags are invalid.")
        memory["tags"] = tags
        memory["importance"] = int(memory["importance"])
        memory["excluded"] = bool(memory["excluded"])
        return memory

    @staticmethod
    def _create_link_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_links (
                id TEXT PRIMARY KEY,
                from_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                to_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                relation TEXT NOT NULL CHECK(length(trim(relation)) BETWEEN 1 AND 120),
                relation_key TEXT NOT NULL,
                strength INTEGER NOT NULL CHECK(strength BETWEEN 1 AND 3),
                created_at TEXT NOT NULL,
                CHECK(from_id <> to_id)
            )
            """
        )

    @staticmethod
    def _create_indexes(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_updated_at "
            "ON memories(updated_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_links_from ON memory_links(from_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_links_to ON memory_links(to_id)"
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_links_equivalent
            ON memory_links(
                CASE WHEN from_id < to_id THEN from_id ELSE to_id END,
                CASE WHEN from_id < to_id THEN to_id ELSE from_id END,
                relation_key
            )
            """
        )

    def _migrate_legacy_memories(self, connection: sqlite3.Connection) -> int:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(memories)").fetchall()
        }
        required_legacy_columns = {
            "id",
            "title",
            "content",
            "category",
            "created_at",
            "updated_at",
        }
        if not required_legacy_columns.issubset(columns):
            raise RuntimeError("The existing memory table has an unsupported schema.")

        connection.execute("DROP TABLE IF EXISTS memories_v2_migration")
        connection.execute(_memory_table_sql("memories_v2_migration"))
        rows = connection.execute("SELECT * FROM memories").fetchall()
        for row in rows:
            old = dict(row)
            category = str(old["category"])
            if category in LEGACY_CATEGORY_MAP:
                category = LEGACY_CATEGORY_MAP[category]
            if category not in MEMORY_CATEGORIES:
                raise RuntimeError("A stored memory has an unsupported category.")

            tags = old.get("tags", "[]")
            if isinstance(tags, str):
                tags = json.loads(tags)
            if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                raise RuntimeError("A stored memory has invalid tags.")

            values = {
                "id": old["id"],
                "title": old["title"],
                "content": old["content"],
                "category": category,
                "source_type": old.get("source_type") or "saved",
                "source": old.get("source"),
                "verification": old.get("verification") or "to_verify",
                "tags": json.dumps(tags, ensure_ascii=False),
                "importance": old.get("importance", 3),
                "excluded": int(bool(old.get("excluded", 0))),
                "conversation_id": old.get("conversation_id"),
                "last_used": old.get("last_used"),
                "created_at": old["created_at"],
                "updated_at": old["updated_at"],
            }
            connection.execute(
                """
                INSERT INTO memories_v2_migration (
                    id, title, content, category, source_type, source,
                    verification, tags, importance, excluded, conversation_id,
                    last_used, created_at, updated_at
                ) VALUES (
                    :id, :title, :content, :category, :source_type, :source,
                    :verification, :tags, :importance, :excluded, :conversation_id,
                    :last_used, :created_at, :updated_at
                )
                """,
                values,
            )

        connection.execute("DROP TABLE memories")
        connection.execute(
            "ALTER TABLE memories_v2_migration RENAME TO memories"
        )
        return len(rows)

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

    @staticmethod
    def _validate_current_schema(connection: sqlite3.Connection) -> None:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not {"memories", "memory_links"}.issubset(tables):
            raise RuntimeError("The local memory database is incomplete.")
        required_memory_columns = {
            "id",
            "title",
            "content",
            "category",
            "source_type",
            "source",
            "verification",
            "tags",
            "importance",
            "excluded",
            "conversation_id",
            "last_used",
            "created_at",
            "updated_at",
        }
        required_link_columns = {
            "id",
            "from_id",
            "to_id",
            "relation",
            "relation_key",
            "strength",
            "created_at",
        }
        memory_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(memories)").fetchall()
        }
        link_columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(memory_links)"
            ).fetchall()
        }
        if (
            not required_memory_columns.issubset(memory_columns)
            or not required_link_columns.issubset(link_columns)
        ):
            raise RuntimeError("The local memory database is incomplete.")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5)
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
