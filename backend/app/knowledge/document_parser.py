"""Document parser for J.A.C.K. M4.3 Document Intelligence.

Supports: PDF, DOCX, TXT, Markdown, HTML.
Security: file size limits, path traversal protection, MIME validation,
ZIP bomb protection, empty/corrupted file handling.
"""

from __future__ import annotations

import hashlib
import html
import logging
import mimetypes
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import docx
from pypdf import PdfReader

logger = logging.getLogger("jack.backend.knowledge")

# Security limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_EXTRACTED_CHARS = 1_000_000  # 1M chars per document
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/html",
    "application/xhtml+xml",
}

EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
}


@dataclass
class ParsedDocument:
    title: str
    content: str
    metadata: dict[str, object]
    pages: list[dict[str, object]] = field(default_factory=list)
    sections: list[dict[str, object]] = field(default_factory=list)
    char_count: int = 0
    word_count: int = 0


class DocumentParseError(Exception):
    pass


class DocumentSecurityError(Exception):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def validate_file(path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """Validate file existence, size, extension, and path traversal."""
    if not path.exists():
        raise DocumentSecurityError(f"File not found: {path}")
    if not path.is_file():
        raise DocumentSecurityError(f"Not a regular file: {path}")

    resolved = path.resolve()
    # Path traversal protection
    if ".." in str(path):
        raise DocumentSecurityError(f"Path traversal detected: {path}")

    size = path.stat().st_size
    if size == 0:
        raise DocumentSecurityError("Empty file")
    if size > max_size:
        raise DocumentSecurityError(
            f"File too large: {size} bytes (max {max_size})"
        )


def detect_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        ext = path.suffix.lower()
        mime = EXTENSION_TO_MIME.get(ext, "application/octet-stream")
    return mime


def validate_mime_type(mime: str, extension: str) -> None:
    ext = extension.lower()
    expected = EXTENSION_TO_MIME.get(ext)
    if expected and mime not in (expected, "application/octet-stream"):
        raise DocumentSecurityError(
            f"MIME type mismatch: {mime} for {ext}"
        )


def _check_zip_bomb(path: Path) -> None:
    """ZIP bomb protection for archive-based formats (docx is a zip)."""
    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path, "r") as zf:
                total_uncompressed = 0
                total_files = 0
                for info in zf.infolist():
                    total_uncompressed += info.file_size
                    total_files += 1
                    if total_uncompressed > 100 * 1024 * 1024:
                        raise DocumentSecurityError(
                            "ZIP bomb detected: uncompressed size too large"
                        )
                    if total_files > 10000:
                        raise DocumentSecurityError(
                            "ZIP bomb detected: too many files"
                        )
        except zipfile.BadZipFile:
            raise DocumentSecurityError("Corrupted ZIP/DOCX file")


def parse_pdf(path: Path) -> ParsedDocument:
    reader = PdfReader(str(path))
    pages = []
    full_text = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            logger.warning("Failed to extract text from PDF page %d", i + 1)
            text = ""
        pages.append(
            {
                "page_number": i + 1,
                "text": text,
                "char_count": len(text),
            }
        )
        full_text.append(text)
    content = "\n\n".join(full_text)
    title = path.stem
    metadata = {
        "source_type": "document",
        "document_type": "pdf",
        "page_count": len(reader.pages),
    }
    return ParsedDocument(
        title=title,
        content=content,
        metadata=metadata,
        pages=pages,
        char_count=len(content),
        word_count=len(content.split()),
    )


def parse_docx(path: Path) -> ParsedDocument:
    _check_zip_bomb(path)
    doc = docx.Document(str(path))
    paragraphs = []
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
            full_text.append(para.text)
    content = "\n\n".join(full_text)
    title = path.stem
    metadata = {
        "source_type": "document",
        "document_type": "docx",
        "paragraph_count": len(paragraphs),
    }
    return ParsedDocument(
        title=title,
        content=content,
        metadata=metadata,
        char_count=len(content),
        word_count=len(content.split()),
    )


def parse_txt(path: Path) -> ParsedDocument:
    content = path.read_text(encoding="utf-8", errors="replace")
    title = path.stem
    metadata = {
        "source_type": "document",
        "document_type": "txt",
    }
    return ParsedDocument(
        title=title,
        content=content,
        metadata=metadata,
        char_count=len(content),
        word_count=len(content.split()),
    )


def parse_md(path: Path) -> ParsedDocument:
    content = path.read_text(encoding="utf-8", errors="replace")
    title = path.stem
    first_heading = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    if first_heading:
        title = first_heading.group(1).strip()
    metadata = {
        "source_type": "document",
        "document_type": "md",
    }
    return ParsedDocument(
        title=title,
        content=content,
        metadata=metadata,
        char_count=len(content),
        word_count=len(content.split()),
    )


def parse_html(path: Path) -> ParsedDocument:
    content = path.read_text(encoding="utf-8", errors="replace")

    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.text: list[str] = []

        def handle_data(self, data: str) -> None:
            self.text.append(data)

    extractor = TextExtractor()
    extractor.feed(content)
    plain_text = "".join(extractor.text)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    title = path.stem
    title_match = re.search(
        r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL
    )
    if title_match:
        title = html.unescape(title_match.group(1)).strip()

    metadata = {
        "source_type": "document",
        "document_type": "html",
    }
    return ParsedDocument(
        title=title,
        content=plain_text,
        metadata=metadata,
        char_count=len(plain_text),
        word_count=len(plain_text.split()),
    )


def parse_document(path: Path | str) -> ParsedDocument:
    """Main entry point: validate, detect format, parse document."""
    path = Path(path)
    validate_file(path)

    extension = path.suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentSecurityError(
            f"Unsupported file extension: {extension}"
        )

    mime = detect_mime_type(path)
    validate_mime_type(mime, extension)

    content_hash = _sha256_file(path)

    if extension == ".pdf":
        result = parse_pdf(path)
    elif extension == ".docx":
        result = parse_docx(path)
    elif extension == ".txt":
        result = parse_txt(path)
    elif extension == ".md":
        result = parse_md(path)
    elif extension in (".html", ".htm"):
        result = parse_html(path)
    else:
        raise DocumentSecurityError(f"Unsupported file extension: {extension}")

    # Truncate if too large
    if len(result.content) > MAX_EXTRACTED_CHARS:
        result.content = result.content[:MAX_EXTRACTED_CHARS]
        result.char_count = len(result.content)
        result.word_count = len(result.content.split())

    result.metadata["content_hash"] = content_hash
    result.metadata["file_name"] = path.name
    result.metadata["file_size"] = path.stat().st_size
    result.metadata["mime_type"] = mime

    return result
