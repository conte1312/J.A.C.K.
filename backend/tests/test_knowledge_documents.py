"""J.A.C.K. M4.3 Document Intelligence tests.

Tests for document parsing, chunking, ingestion pipeline, and document API.
Uses isolated temporary files and databases. Never touches real user data.
"""

from __future__ import annotations

import hashlib
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.routes.v2.knowledge import (
    delete_document,
    get_document,
    get_document_chunks,
    import_document_file,
    list_documents,
    reprocess_document,
)
from app.api.schemas.knowledge import (
    DocumentImportRequest,
    DocumentReprocessRequest,
)
from app.knowledge.chunking import DocumentChunker
from app.knowledge.document_parser import (
    DocumentParseError,
    DocumentSecurityError,
    ParsedDocument,
    parse_document,
)
from app.knowledge.document_service import DocumentService, DocumentImportResult
from app.knowledge.repository import KnowledgeRepository


def _make_temp_file(content: bytes, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


def _make_request(repository: KnowledgeRepository) -> MagicMock:
    request = MagicMock()
    request.app.state.knowledge_repository = repository
    return request


class DocumentParserTests(unittest.TestCase):
    """Tests for document parsers (M4.3)."""

    def setUp(self) -> None:
        self.temp_files: list[Path] = []

    def tearDown(self) -> None:
        for f in self.temp_files:
            try:
                f.unlink()
            except OSError:
                pass
        self.temp_files = []

    # ---- TXT ----

    def test_parse_txt(self) -> None:
        f = _make_temp_file(b"Hello world\nThis is a test.", ".txt")
        self.temp_files.append(f)
        doc = parse_document(f)
        self.assertEqual(doc.title, f.stem)
        self.assertIn("Hello world", doc.content)
        self.assertEqual(doc.metadata["document_type"], "txt")

    def test_parse_txt_empty_raises(self) -> None:
        f = _make_temp_file(b"", ".txt")
        self.temp_files.append(f)
        with self.assertRaises(DocumentSecurityError):
            parse_document(f)

    # ---- Markdown ----

    def test_parse_md(self) -> None:
        f = _make_temp_file(
            b"# My Document\n\nSome content here.\n\n## Section\nMore text.", ".md"
        )
        self.temp_files.append(f)
        doc = parse_document(f)
        self.assertEqual(doc.title, "My Document")
        self.assertIn("Some content here", doc.content)

    # ---- HTML ----

    def test_parse_html(self) -> None:
        f = _make_temp_file(
            b"<html><head><title>Page Title</title></head>"
            b"<body><h1>Hello</h1><p>Content</p></body></html>",
            ".html",
        )
        self.temp_files.append(f)
        doc = parse_document(f)
        self.assertEqual(doc.title, "Page Title")
        self.assertIn("Hello", doc.content)
        self.assertIn("Content", doc.content)

    # ---- Security: unsupported extension ----

    def test_parse_unsupported_extension(self) -> None:
        f = _make_temp_file(b"content", ".xyz")
        self.temp_files.append(f)
        with self.assertRaises(DocumentSecurityError):
            parse_document(f)

    # ---- Security: path traversal ----

    def test_parse_path_traversal(self) -> None:
        with self.assertRaises(DocumentSecurityError):
            parse_document(Path("/etc/passwd"))

    # ---- Security: file too large ----

    def test_parse_file_too_large(self) -> None:
        f = _make_temp_file(b"x" * (60 * 1024 * 1024), ".txt")
        self.temp_files.append(f)
        with self.assertRaises(DocumentSecurityError):
            parse_document(f)

    # ---- Content hash ----

    def test_parse_content_hash(self) -> None:
        content = b"Deterministic content for hashing"
        f = _make_temp_file(content, ".txt")
        self.temp_files.append(f)
        doc = parse_document(f)
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(doc.metadata["content_hash"], expected)

    # ---- Duplicate detection via hash ----

    def test_parse_same_content_same_hash(self) -> None:
        content = b"Same content"
        f1 = _make_temp_file(content, ".txt")
        f2 = _make_temp_file(content, ".txt")
        self.temp_files.extend([f1, f2])
        d1 = parse_document(f1)
        d2 = parse_document(f2)
        self.assertEqual(d1.metadata["content_hash"], d2.metadata["content_hash"])


class DocumentChunkerTests(unittest.TestCase):
    """Tests for document chunking (M4.3)."""

    def setUp(self) -> None:
        self.chunker = DocumentChunker(chunk_size=200, chunk_overlap=50)

    def _make_document(self, content: str) -> ParsedDocument:
        return ParsedDocument(
            title="Test",
            content=content,
            metadata={},
            char_count=len(content),
            word_count=len(content.split()),
        )

    def test_chunk_short_document(self) -> None:
        doc = self._make_document("Short content.")
        result = self.chunker.chunk_document(doc)
        self.assertEqual(result.total_chunks, 1)
        self.assertEqual(result.chunks[0].content, "Short content.")
        self.assertEqual(result.chunks[0].order, 0)

    def test_chunk_preserves_order(self) -> None:
        doc = self._make_document(
            "First paragraph with some content here.\n\n"
            "Second paragraph with more content here.\n\n"
            "Third paragraph with additional content here.\n\n"
            "Fourth paragraph to ensure multiple chunks.\n\n"
            "Fifth paragraph for good measure.\n\n"
            "Sixth paragraph to push over the limit.\n"
        )
        result = self.chunker.chunk_document(doc)
        self.assertGreater(result.total_chunks, 1)
        orders = [c.order for c in result.chunks]
        self.assertEqual(orders, list(range(len(orders))))

    def test_chunk_respects_size(self) -> None:
        long_text = "Word " * 500  # ~3000 chars
        doc = self._make_document(long_text)
        result = self.chunker.chunk_document(doc)
        max_size = self.chunker.chunk_size + 100
        for chunk in result.chunks:
            self.assertLessEqual(len(chunk.content), max_size)

    def test_chunk_empty_document(self) -> None:
        doc = self._make_document("")
        result = self.chunker.chunk_document(doc)
        self.assertEqual(result.total_chunks, 0)

    def test_chunk_invalid_size(self) -> None:
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=50, chunk_overlap=10)
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=100, chunk_overlap=100)


class DocumentServiceTests(unittest.TestCase):
    """Tests for document ingestion service (M4.3)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-doc-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = DocumentService(repository=self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _make_txt_file(self, content: str, name: str) -> Path:
        f = Path(self.temp_dir.name) / name
        f.write_text(content, encoding="utf-8")
        return f

    # ---- Import ----

    def test_import_txt_document(self) -> None:
        f = self._make_txt_file(
            "Project Alpha\n\nThis is a test document about Project Alpha.\n"
            "It contains important information.\n",
            "test_alpha.txt",
        )
        result = self.service.import_document(f)
        self.assertEqual(result.status, "imported")
        self.assertEqual(result.document_title, "test_alpha")
        self.assertGreater(result.chunks_created, 0)
        self.assertGreater(result.items_created, 0)
        self.assertIsNotNone(result.content_hash)

    def test_import_duplicate_document(self) -> None:
        f = self._make_txt_file("Unique content for duplicate test.", "dup.txt")
        result1 = self.service.import_document(f)
        self.assertEqual(result1.status, "imported")
        result2 = self.service.import_document(f)
        self.assertEqual(result2.status, "duplicate")
        self.assertEqual(result2.chunks_created, 0)
        self.assertEqual(result2.items_created, 0)
        self.assertEqual(result1.source_id, result2.source_id)

    def test_import_nonexistent_file(self) -> None:
        with self.assertRaises(DocumentSecurityError):
            self.service.import_document(Path("/nonexistent/file.txt"))

    def test_import_unsupported_extension(self) -> None:
        f = self._make_txt_file("content", "test.xyz")
        with self.assertRaises(DocumentSecurityError):
            self.service.import_document(f)

    # ---- Sources ----

    def test_list_sources(self) -> None:
        f = self._make_txt_file("Source list test.", "list.txt")
        self.service.import_document(f)
        sources = self.service.list_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "list")

    def test_get_source(self) -> None:
        f = self._make_txt_file("Get source test.", "get.txt")
        result = self.service.import_document(f)
        source = self.service.get_source(result.source_id)
        self.assertIsNotNone(source)
        self.assertEqual(source["id"], result.source_id)
        self.assertEqual(source["title"], "get")

    def test_get_source_nonexistent(self) -> None:
        self.assertIsNone(self.service.get_source("nonexistent-id"))

    # ---- Chunks ----

    def test_list_chunks(self) -> None:
        f = self._make_txt_file(
            "Chunk test paragraph one.\n\nChunk test paragraph two.\n",
            "chunks.txt",
        )
        result = self.service.import_document(f)
        chunks = self.service.list_chunks(result.source_id)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]["source_id"], result.source_id)
        self.assertIsInstance(chunks[0]["chunk_index"], int)

    def test_delete_source(self) -> None:
        f = self._make_txt_file("Delete source test.", "delete.txt")
        result = self.service.import_document(f)
        self.assertTrue(service_delete_source(self.service, result.source_id))
        self.assertIsNone(self.service.get_source(result.source_id))

    def test_delete_nonexistent_source(self) -> None:
        self.assertFalse(service_delete_source(self.service, "nonexistent-id"))


def service_delete_source(service: DocumentService, source_id: str) -> bool:
    return service.delete_source(source_id)


# ---- API Tests ----

class DocumentApiTests(unittest.TestCase):
    """Tests for M4.3 Document API routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-doc-api-test-")
        self.database_path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.repository = KnowledgeRepository(self.database_path)
        self.repository.initialize()
        self.service = DocumentService(repository=self.repository)
        self.request = _make_request(self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _make_txt_file(self, content: str, name: str) -> Path:
        f = Path(self.temp_dir.name) / name
        f.write_text(content, encoding="utf-8")
        return f

    def test_api_import_document_file(self) -> None:
        f = self._make_txt_file(
            "API import test document.\n\nSecond paragraph here.",
            "api_test.txt",
        )
        result = import_document_file(
            file_path=str(f),
            service=self.service,
        )
        self.assertEqual(result["status"], "imported")
        self.assertEqual(result["document_title"], "api_test")
        self.assertGreater(result["chunks_created"], 0)
        self.assertGreater(result["items_created"], 0)

    def test_api_import_document_file_missing(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            import_document_file(
                file_path="/nonexistent/file.txt",
                service=self.service,
            )
        self.assertEqual(ctx.exception.status_code, 422)

    def test_api_import_document_duplicate(self) -> None:
        f = self._make_txt_file("Duplicate API test.", "dup_api.txt")
        r1 = import_document_file(file_path=str(f), service=self.service)
        self.assertEqual(r1["status"], "imported")
        r2 = import_document_file(file_path=str(f), service=self.service)
        self.assertEqual(r2["status"], "duplicate")
        self.assertEqual(r2["chunks_created"], 0)

    def test_api_list_documents(self) -> None:
        f = self._make_txt_file("List documents test.", "list_api.txt")
        import_document_file(file_path=str(f), service=self.service)
        sources = list_documents(service=self.service)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "list_api")

    def test_api_get_document(self) -> None:
        f = self._make_txt_file("Get document test.", "get_api.txt")
        result = import_document_file(file_path=str(f), service=self.service)
        source = get_document(result["source_id"], self.service)
        self.assertIsNotNone(source)
        self.assertEqual(source["id"], result["source_id"])

    def test_api_get_document_nonexistent(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_document("nonexistent-id", self.service)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_get_document_chunks(self) -> None:
        f = self._make_txt_file(
            "Chunk A content.\n\nChunk B content.\n", "chunks_api.txt"
        )
        result = import_document_file(file_path=str(f), service=self.service)
        chunks = get_document_chunks(result["source_id"], self.service)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]["source_id"], result["source_id"])

    def test_api_reprocess_document(self) -> None:
        f = self._make_txt_file("Reprocess test v1.", "reproc.txt")
        r1 = import_document_file(file_path=str(f), service=self.service)
        self.assertEqual(r1["status"], "imported")
        # Reprocess with skip_duplicate=False should re-import
        payload = DocumentReprocessRequest(skip_duplicate=False)
        r2 = reprocess_document(
            source_id=r1["source_id"],
            payload=payload,
            service=self.service,
        )
        self.assertEqual(r2["status"], "imported")

    def test_api_delete_document(self) -> None:
        f = self._make_txt_file("Delete API test.", "del_api.txt")
        result = import_document_file(file_path=str(f), service=self.service)
        self.assertTrue(delete_document(result["source_id"], self.service))
        with self.assertRaises(HTTPException) as ctx:
            get_document(result["source_id"], self.service)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
