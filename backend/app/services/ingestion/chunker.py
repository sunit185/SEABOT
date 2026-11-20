"""
chunker.py — Token-aware text chunker using tiktoken (cl100k_base).
"""
from __future__ import annotations

import uuid
from typing import Any

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the number of tokens in *text*."""
    return len(_ENC.encode(text))


def chunk_text(
    text: str,
    max_tokens: int = 600,
    overlap_tokens: int = 100,
) -> list[str]:
    """
    Split *text* into overlapping token windows.

    Each window is at most *max_tokens* tokens long.  Consecutive windows
    share *overlap_tokens* tokens so that context is not lost at boundaries.
    """
    if not text or not text.strip():
        return []

    tokens = _ENC.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_str = _ENC.decode(chunk_tokens)
        chunks.append(chunk_str)
        if end == len(tokens):
            break
        start = end - overlap_tokens
        if start < 0:
            start = 0

    return chunks


def create_chunks(
    pages: list[dict[str, Any]],
    doc_id: str,
    doc_name: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[dict[str, Any]]:
    """
    Turn a list of page dicts into chunk dicts ready for indexing.

    Each *page* dict must contain:
        page_num        : int
        text            : str
        bbox            : list[float] | None
        section_heading : str | None
        chunk_type      : str   ("text" | "table" | "diagram" | "sheet_rows")

    Text is NEVER merged across different pages.

    Returns a list of chunk dicts with:
        chunk_id, doc_id, doc_name, page, section_heading,
        chunk_type, bbox, text
    """
    result: list[dict[str, Any]] = []

    for page in pages:
        page_num: int = page.get("page_num", 0)
        raw_text: str = page.get("text", "") or ""
        bbox = page.get("bbox")
        section_heading: str | None = page.get("section_heading")
        chunk_type: str = page.get("chunk_type", "text")

        # Also index any tables found on this page as separate chunks
        tables: list[str] = page.get("tables", [])
        for table_md in tables:
            if not table_md.strip():
                continue
            result.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": page_num,
                    "section_heading": section_heading,
                    "chunk_type": "table",
                    "bbox": bbox,
                    "text": table_md,
                }
            )

        # Chunk the main text of this page
        if not raw_text.strip():
            continue

        sub_chunks = chunk_text(raw_text, max_tokens=chunk_size, overlap_tokens=overlap)
        for sub in sub_chunks:
            if not sub.strip():
                continue
            result.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": page_num,
                    "section_heading": section_heading,
                    "chunk_type": chunk_type,
                    "bbox": bbox,
                    "text": sub,
                }
            )

    return result
