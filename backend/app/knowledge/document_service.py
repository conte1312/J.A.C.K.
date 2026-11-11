"""Document ingestion pipeline for J.A.C.K. M4.3 Document Intelligence.

Orchestrates: validate → extract → normalize → chunk → register → integrate.
Uses KnowledgeRepository for items/domains and direct SQLite for sources/chunks.
Never modifies KnowledgeRepository; reads/writes knowledge_sources and
document_chunks tables directly through dedicated connections.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.knowledge.chunking import DocumentChunker
from app.knowledge.document_parser import (
    DocumentParseError,
    DocumentSecurityError,
    ParsedDocument,
    parse_document,
)
from app.knowledge.embeddings import EmbeddingProvider
from app.knowledge.repository import KnowledgeNotFoundError, KnowledgeRepository
from app.knowledge.vector_store import VectorStore

logger = logging.getLogger("jack.backend.knowledge")

DEFAULT_DOMAIN_NAME = "Imported Documents"
DEFAULT_DOMAIN_SLUG = "imported-documents"


@dataclass
class DocumentImportResult:
    source_id: str
    document_title: str
    document_type: str
    chunks_created: int
    items_created: int
    content_hash: str
    status: str  # "imported", "duplicate", "error"


class DocumentService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.repository = repository
        self.chunker = DocumentChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self._default_domain_id: str | None = None
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    # ------------------------------------------------------------------
    # Pipeline entry point
    # ------------------------------------------------------------------

    def import_document(
        self,
        file_path: Path | str,
        domain_id: str | None = None,
        skip_duplicate: bool = True,
    ) -> DocumentImportResult:
        """Full pipeline: validate → extract → chunk → register → integrate.

        Never modifies M3. Writes only to knowledge.sqlite3 tables
        (knowledge_sources, document_chunks, knowledge_items via repository).
        """
        path = Path(file_path)

        # Stage 1: Parse (validate + extract + normalize)
        try:
            parsed = parse_document(path)
        except (DocumentSecurityError, DocumentParseError) as error:
            logger.error("Document parse failed for %s: %s", path, error)
            raise

        content_hash = str(parsed.metadata.get("content_hash", ""))

        # Stage 2: Duplicate detection
        if skip_duplicate and content_hash:
            existing = self._find_source_by_hash(content_hash)
            if existing:
                logger.info(
                    "Duplicate document skipped: %s (hash %s)",
                    path.name,
                    content_hash[:16],
                )
                return DocumentImportResult(
                    source_id=existing["id"],
                    document_title=str(existing["title"]),
                    document_type=str(existing["document_type"]),
                    chunks_created=0,
                    items_created=0,
                    content_hash=content_hash,
                    status="duplicate",
                )

        # Stage 3: Resolve domain
        target_domain_id = domain_id or self._ensure_default_domain()

        # Stage 4: Register source
        source_id = self._register_source(
            parsed, path, content_hash, target_domain_id
        )

        # Stage 5: Chunk
        chunking_result = self.chunker.chunk_document(parsed)

        # Stage 6: Store chunks and create knowledge items
        items_created = 0
        for chunk in chunking_result.chunks:
            chunk_id = self._store_chunk(source_id, chunk)
            try:
                item = self.repository.create_item(
                    title=f"{parsed.title} - Chunk {chunk.order + 1}",
                    content=chunk.content,
                    domain_id=target_domain_id,
                    knowledge_type="concept",
                    source_type="document",
                    source_id=source_id,
                    tags=[],
                    importance=3,
                    excluded=False,
                )
                items_created += 1
                # Generate and store embedding if provider available
                if (
                    self.vector_store is not None
                    and self.embedding_provider is not None
                    and item is not None
                ):
                    try:
                        emb = self.embedding_provider.embed_text(chunk.content)
                        self.vector_store.store_embedding(
                            item_id=str(item["id"]),
                            vector=emb.vector,
                            model_name=emb.model,
                            model_version=emb.model_version,
                            chunk_id=chunk_id,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to store embedding for item %s",
                            item["id"],
                        )
            except Exception:
                logger.exception(
                    "Failed to create knowledge item for chunk %d", chunk.order
                )

        return DocumentImportResult(
            source_id=source_id,
            document_title=parsed.title,
            document_type=str(parsed.metadata.get("document_type", "unknown")),
            chunks_created=chunking_result.total_chunks,
            items_created=items_created,
            content_hash=content_hash,
            status="imported",
        )

    # ------------------------------------------------------------------
    # Source management (direct SQLite, knowledge_sources table)
    # ------------------------------------------------------------------

    def _ensure_default_domain(self) -> str:
        if self._default_domain_id is not None:
            return self._default_domain_id
        existing = self.repository.list_domains()
        for d in existing:
            if d.get("slug") == DEFAULT_DOMAIN_SLUG:
                self._default_domain_id = str(d["id"])
                return self._default_domain_id
        created = self.repository.create_domain(
            name=DEFAULT_DOMAIN_NAME,
            slug=DEFAULT_DOMAIN_SLUG,
            description="Documents imported via Knowledge Core",
        )
        self._default_domain_id = str(created["id"])
        return self._default_domain_id

    def _ensure_content_hash_column(self) -> None:
        """Add content_hash column to knowledge_sources if missing (safe migration)."""
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(knowledge_sources)"
                ).fetchall()
            }
            if "content_hash" not in columns:
                connection.execute(
                    "ALTER TABLE knowledge_sources ADD COLUMN content_hash TEXT"
                )
                connection.commit()

    def _find_source_by_hash(self, content_hash: str) -> dict[str, object] | None:
        self._ensure_content_hash_column()
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute(
                """
                SELECT id, title, document_type, content_hash
                FROM knowledge_sources
                WHERE content_hash = ?
                LIMIT 1
                """,
                (content_hash,),
            ).fetchone()
        return dict(row) if row is not None else None

    def _register_source(
        self,
        parsed: ParsedDocument,
        path: Path,
        content_hash: str,
        domain_id: str,
    ) -> str:
        self._ensure_content_hash_column()
        source_id = str(uuid.uuid4())
        now = self._now_iso()
        metadata = dict(parsed.metadata)
        metadata["imported_at"] = now
        metadata["file_path"] = str(path)

        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO knowledge_sources
                (id, title, document_type, file_path, url, author, publisher,
                 published_at, accessed_at, authority_score, language,
                 page_count, created_at, updated_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    parsed.title,
                    str(parsed.metadata.get("document_type", "unknown")),
                    str(path),
                    None,
                    None,
                    None,
                    None,
                    now,
                    None,
                    None,
                    int(parsed.metadata.get("page_count") or 0) or None,
                    now,
                    now,
                    content_hash,
                ),
            )
            connection.commit()
        logger.info("Source registered: %s (%s)", source_id, parsed.title)
        return source_id

    def _store_chunk(self, source_id: str, chunk: Any) -> str:
        chunk_id = str(uuid.uuid4())
        now = self._now_iso()
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO document_chunks
                (id, source_id, item_id, chunk_index, content, page_number,
                 section_title, char_start, char_end, embedding_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    source_id,
                    None,
                    chunk.order,
                    chunk.content,
                    chunk.page_number,
                    chunk.section_title,
                    chunk.char_start,
                    chunk.char_end,
                    None,
                    now,
                ),
            )
            connection.commit()
        return chunk_id

    def _now_iso(self) -> str:
        return datetime.now().isoformat(timespec="milliseconds")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_sources(self) -> list[dict[str, object]]:
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT id, title, document_type, file_path, created_at,
                       updated_at, content_hash, page_count
                FROM knowledge_sources
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_source(self, source_id: str) -> dict[str, object] | None:
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute(
                "SELECT * FROM knowledge_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_chunks(self, source_id: str) -> list[dict[str, object]]:
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            rows = connection.execute(
                """
                SELECT id, source_id, item_id, chunk_index, content,
                       page_number, section_title, char_start, char_end,
                       embedding_id, created_at
                FROM document_chunks
                WHERE source_id = ?
                ORDER BY chunk_index ASC
                """,
                (source_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_source(self, source_id: str) -> bool:
        """Archive source and its chunks (soft delete via referential integrity).

        Physical DELETE cascades to chunks (ON DELETE CASCADE). Items created
        from chunks remain archived (not physically deleted) per M3/M4 policy.
        """
        existing = self.get_source(source_id)
        if existing is None:
            return False
        with sqlite3.connect(
            self.repository.database_path, timeout=10
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                "DELETE FROM knowledge_sources WHERE id = ?",
                (source_id,),
            )
            connection.commit()
            return cursor.rowcount > 0
