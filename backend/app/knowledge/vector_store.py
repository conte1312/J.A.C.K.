"""SQLite vector store for J.A.C.K. M4.4 Semantic Retrieval.

Stores embedding vectors linked to knowledge items and chunks.
Uses a dedicated table; no separate database server.
Supports re-embedding when model changes.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.knowledge.embeddings import EmbeddingResult, cosine_similarity

logger = logging.getLogger("jack.backend.knowledge")


@dataclass
class EmbeddingRecord:
    id: str
    item_id: str
    chunk_id: str | None
    model_name: str
    model_version: str
    dimensions: int
    vector: list[float]
    created_at: str


class VectorStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
                    chunk_id TEXT REFERENCES document_chunks(id) ON DELETE CASCADE,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_item "
                "ON knowledge_embeddings(item_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_chunk "
                "ON knowledge_embeddings(chunk_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_model "
                "ON knowledge_embeddings(model_name, model_version)"
            )
            connection.commit()

    def _serialize(self, vector: list[float]) -> str:
        return json.dumps(vector)

    def _deserialize(self, data: str) -> list[float]:
        return json.loads(data)

    def store_embedding(
        self,
        item_id: str,
        vector: list[float],
        model_name: str,
        model_version: str,
        chunk_id: str | None = None,
    ) -> str:
        embedding_id = str(__import__("uuid").uuid4())
        now = __import__("datetime").datetime.now().isoformat(timespec="milliseconds")
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                """
                INSERT INTO knowledge_embeddings
                (id, item_id, chunk_id, model_name, model_version,
                 dimensions, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    embedding_id,
                    item_id,
                    chunk_id,
                    model_name,
                    model_version,
                    len(vector),
                    self._serialize(vector),
                    now,
                ),
            )
            connection.commit()
        return embedding_id

    def get_embedding(self, embedding_id: str) -> EmbeddingRecord | None:
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute(
                "SELECT * FROM knowledge_embeddings WHERE id = ?",
                (embedding_id,),
            ).fetchone()
        if row is None:
            return None
        return EmbeddingRecord(
            id=str(row["id"]),
            item_id=str(row["item_id"]),
            chunk_id=str(row["chunk_id"]) if row["chunk_id"] else None,
            model_name=str(row["model_name"]),
            model_version=str(row["model_version"]),
            dimensions=int(row["dimensions"]),
            vector=self._deserialize(str(row["embedding"])),
            created_at=str(row["created_at"]),
        )

    def list_embeddings_for_item(self, item_id: str) -> list[EmbeddingRecord]:
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT * FROM knowledge_embeddings
                WHERE item_id = ?
                ORDER BY created_at DESC
                """,
                (item_id,),
            ).fetchall()
        return [
            EmbeddingRecord(
                id=str(r["id"]),
                item_id=str(r["item_id"]),
                chunk_id=str(r["chunk_id"]) if r["chunk_id"] else None,
                model_name=str(r["model_name"]),
                model_version=str(r["model_version"]),
                dimensions=int(r["dimensions"]),
                vector=self._deserialize(str(r["embedding"])),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def delete_embeddings_for_item(self, item_id: str) -> int:
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                "DELETE FROM knowledge_embeddings WHERE item_id = ?",
                (item_id,),
            )
            connection.commit()
            return cursor.rowcount

    def search_similar(
        self,
        query_vector: list[float],
        model_name: str,
        model_version: str,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Return list of (item_id, similarity) sorted descending."""
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT item_id, embedding FROM knowledge_embeddings
                WHERE model_name = ? AND model_version = ?
                """,
                (model_name, model_version),
            ).fetchall()
        results: list[tuple[str, float]] = []
        for row in rows:
            item_id = str(row["item_id"])
            vector = self._deserialize(str(row["embedding"]))
            sim = cosine_similarity(query_vector, vector)
            if sim >= min_similarity:
                results.append((item_id, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def count_embeddings(self) -> int:
        with sqlite3.connect(self.database_path, timeout=10) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS cnt FROM knowledge_embeddings"
            ).fetchone()
        return int(row[0]) if row else 0
