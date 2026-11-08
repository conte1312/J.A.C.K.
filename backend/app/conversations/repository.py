from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("jack.backend.conversations")


class ConversationNotFoundError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


_CONVERSATIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        provider_id TEXT,
        model_id TEXT,
        metadata TEXT NOT NULL DEFAULT '{}'
    )
"""

_CONVERSATION_MESSAGES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS conversation_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL CHECK(length(trim(content)) BETWEEN 1 AND 20000),
        created_at TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0, 1)),
        provider_label TEXT
    )
"""


class ConversationRepository:
    """SQLite-backed store for persistent conversations and their messages."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(_CONVERSATIONS_TABLE_SQL)
            connection.execute(_CONVERSATION_MESSAGES_TABLE_SQL)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id
                ON conversation_messages(conversation_id, created_at ASC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                ON conversations(updated_at DESC)
                """
            )
        self.database_path.chmod(0o600)

    def create_conversation(
        self,
        *,
        title: str,
        provider_id: str | None = None,
        model_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        conversation = {
            "id": str(uuid.uuid4()),
            "title": title,
            "created_at": now,
            "updated_at": now,
            "provider_id": provider_id,
            "model_id": model_id,
            "metadata": metadata or {},
        }
        stored = {
            **conversation,
            "metadata": json.dumps(conversation["metadata"], ensure_ascii=False),
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    id, title, created_at, updated_at,
                    provider_id, model_id, metadata
                ) VALUES (
                    :id, :title, :created_at, :updated_at,
                    :provider_id, :model_id, :metadata
                )
                """,
                stored,
            )
        return self._decode_conversation_row(conversation)

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN conversation_messages m
                    ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.created_at DESC, c.title ASC
                """
            ).fetchall()
        return [self._decode_conversation_row(dict(row)) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return self._decode_conversation_row(dict(row))

    def get_conversation_with_messages(
        self, conversation_id: str
    ) -> dict[str, Any] | None:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at,
                       is_demo, provider_label
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
        messages = [self._decode_message_row(dict(row)) for row in rows]
        conversation["messages"] = messages
        conversation["message_count"] = len(messages)
        return conversation

    def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> dict[str, Any] | None:
        now = _now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, conversation_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        return self._decode_conversation_row(dict(row)) if row is not None else None

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
        return cursor.rowcount > 0

    def add_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        is_demo: bool = False,
        provider_label: str | None = None,
    ) -> dict[str, Any] | None:
        if self.get_conversation(conversation_id) is None:
            return None
        now = _now()
        message = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": now,
            "is_demo": is_demo,
            "provider_label": provider_label,
        }
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, conversation_id),
            )
            connection.execute(
                """
                INSERT INTO conversation_messages (
                    id, conversation_id, role, content, created_at,
                    is_demo, provider_label
                ) VALUES (
                    :id, :conversation_id, :role, :content, :created_at,
                    :is_demo, :provider_label
                )
                """,
                message,
            )
        return self._decode_message_row(message)

    def _decode_conversation_row(
        self, row: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            metadata = json.loads(str(row.get("metadata") or "{}"))
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "provider_id": row["provider_id"],
            "model_id": row["model_id"],
            "metadata": metadata,
            "message_count": int(row.get("message_count") or 0),
        }

    @staticmethod
    def _decode_message_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
            "is_demo": bool(row["is_demo"]),
            "provider_label": row["provider_label"],
        }

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
