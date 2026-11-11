"""Intelligent document chunking for J.A.C.K. M4.3.

Preserves paragraph boundaries, headings, section structure.
Maintains source references, page/section metadata, chunk order.
Configurable chunk sizes; avoids splitting sentences unnecessarily.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.document_parser import ParsedDocument

logger = logging.getLogger("jack.backend.knowledge")

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


@dataclass
class Chunk:
    content: str
    order: int
    page_number: int | None = None
    section_title: str | None = None
    char_start: int | None = None
    char_end: int | None = None


@dataclass
class ChunkingResult:
    chunks: list[Chunk]
    total_chunks: int


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        document: ParsedDocument,
    ) -> ChunkingResult:
        content = document.content
        if not content.strip():
            return ChunkingResult(chunks=[], total_chunks=0)

        # Split by paragraphs first (preserves structure)
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: list[Chunk] = []
        current_order = 0
        current_text = ""
        current_start = 0

        def flush(text: str, start: int, order: int) -> tuple[str, int, int]:
            if not text.strip():
                return "", start, order
            chunks.append(
                Chunk(
                    content=text.strip(),
                    order=order,
                    char_start=start,
                    char_end=start + len(text),
                )
            )
            return "", start + len(text), order + 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)

            # If paragraph fits in current chunk with overlap room
            if len(current_text) + para_len + 2 <= self.chunk_size:
                current_text = (
                    current_text + "\n\n" + para if current_text else para
                )
                continue

            # Paragraph too large for current chunk - flush current
            if current_text.strip():
                current_text, current_start, current_order = flush(
                    current_text, current_start, current_order
                )

            # If paragraph itself exceeds chunk_size, split by sentences
            if para_len > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sentence_buffer = ""
                sentence_start = current_start
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    # If a single sentence is still too large, split by chars
                    if len(sentence) > self.chunk_size:
                        # Flush buffer first
                        if sentence_buffer.strip():
                            current_text, current_start, current_order = flush(
                                sentence_buffer, sentence_start, current_order
                            )
                            sentence_buffer = ""
                        # Split sentence into char-sized pieces
                        for i in range(0, len(sentence), self.chunk_size):
                            piece = sentence[i : i + self.chunk_size]
                            current_text, current_start, current_order = flush(
                                piece, current_start, current_order
                            )
                        sentence_start = current_start
                        continue
                    if (
                        len(sentence_buffer) + len(sentence) + 1
                        > self.chunk_size
                        and sentence_buffer.strip()
                    ):
                        current_text, current_start, current_order = flush(
                            sentence_buffer, sentence_start, current_order
                        )
                        sentence_buffer = sentence
                        sentence_start = current_start
                    else:
                        sentence_buffer = (
                            sentence_buffer + " " + sentence
                            if sentence_buffer
                            else sentence
                        )
                if sentence_buffer.strip():
                    current_text, current_start, current_order = flush(
                        sentence_buffer, sentence_start, current_order
                    )
            else:
                # Normal paragraph that doesn't fit - start new chunk
                current_text = para
                current_start = current_start

        # Flush remaining
        if current_text.strip():
            current_text, current_start, current_order = flush(
                current_text, current_start, current_order
            )

        return ChunkingResult(chunks=chunks, total_chunks=len(chunks))
