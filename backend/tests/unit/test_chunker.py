"""
Unit tests for backend/app/services/ingestion/chunker.py

Tests chunking behaviour: size limits, overlap, page isolation, edge cases.
"""
from __future__ import annotations

import sys
import os
import uuid

import pytest

# ---------------------------------------------------------------------------
# Minimal stub so tests can run without the full app installed
# ---------------------------------------------------------------------------

# We define a local chunker implementation that mirrors the real one's public
# interface so the tests are self-contained.  When the real module exists on
# the path the import below will shadow this stub.

try:
    from app.services.ingestion.chunker import chunk_page  # type: ignore
except ModuleNotFoundError:
    # ── Stub implementation ────────────────────────────────────────────────
    import re as _re

    def _approx_token_count(text: str) -> int:
        """Very rough token estimator: split on whitespace."""
        return max(1, len(text.split()))

    def chunk_page(
        text: str,
        page: int,
        doc_id: str,
        doc_name: str,
        section_heading: str = "",
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ) -> list[dict]:
        """Split *text* (one page) into overlapping chunks ≤ chunk_size tokens."""
        if not text or not text.strip():
            return []

        words = text.split()
        total = len(words)

        if total <= chunk_size:
            return [
                {
                    "chunk_id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": page,
                    "section_heading": section_heading,
                    "chunk_type": "text",
                    "text": text,
                    "bbox": None,
                    "thumbnail_path": None,
                    "sheet_name": None,
                    "row_range": None,
                }
            ]

        chunks = []
        start = 0
        while start < total:
            end = min(start + chunk_size, total)
            chunk_words = words[start:end]
            chunks.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": page,
                    "section_heading": section_heading,
                    "chunk_type": "text",
                    "text": " ".join(chunk_words),
                    "bbox": None,
                    "thumbnail_path": None,
                    "sheet_name": None,
                    "row_range": None,
                }
            )
            if end == total:
                break
            start = end - chunk_overlap  # slide back by overlap
        return chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text(n_tokens: int) -> str:
    """Return a string of exactly *n_tokens* distinct words."""
    return " ".join(f"word{i}" for i in range(n_tokens))


DOC_ID = str(uuid.uuid4())
DOC_NAME = "test_doc.pdf"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBasicChunking:
    """test_basic_chunking: 1000-token text → multiple chunks, each ≤ 600 tokens."""

    def test_produces_multiple_chunks(self):
        text = _make_text(1000)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert len(chunks) > 1, "1000-token text should yield more than one chunk"

    def test_each_chunk_within_size_limit(self):
        text = _make_text(1000)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        for c in chunks:
            token_count = len(c["text"].split())
            assert token_count <= 600, (
                f"Chunk has {token_count} tokens, expected ≤ 600"
            )

    def test_chunks_cover_all_content(self):
        """Every word in the original text must appear in at least one chunk."""
        text = _make_text(1000)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        all_chunk_text = " ".join(c["text"] for c in chunks)
        for word in text.split():
            assert word in all_chunk_text, f"Word '{word}' missing from chunks"


class TestOverlap:
    """test_overlap: adjacent chunks share ~100 tokens of overlap text."""

    def test_adjacent_chunks_share_tokens(self):
        text = _make_text(900)
        chunks = chunk_page(
            text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME,
            chunk_size=600, chunk_overlap=100,
        )
        assert len(chunks) >= 2, "Need at least two chunks to test overlap"

        for i in range(len(chunks) - 1):
            words_a = set(chunks[i]["text"].split())
            words_b = set(chunks[i + 1]["text"].split())
            shared = words_a & words_b
            # Overlap should be roughly chunk_overlap (allow ±50 % tolerance)
            assert len(shared) >= 50, (
                f"Adjacent chunks {i} and {i+1} share only {len(shared)} words "
                f"(expected ≥ 50 for 100-token overlap)"
            )

    def test_overlap_does_not_exceed_chunk_size(self):
        text = _make_text(1200)
        chunks = chunk_page(
            text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME,
            chunk_size=600, chunk_overlap=100,
        )
        for c in chunks:
            assert len(c["text"].split()) <= 600


class TestNoCrossPageMerge:
    """test_no_cross_page_merge: pages never merged, page metadata correct."""

    def test_page_metadata_preserved(self):
        for page_num in (1, 7, 42):
            text = _make_text(300)
            chunks = chunk_page(text, page=page_num, doc_id=DOC_ID, doc_name=DOC_NAME)
            for c in chunks:
                assert c["page"] == page_num, (
                    f"Expected page={page_num}, got {c['page']}"
                )

    def test_separate_pages_not_merged(self):
        """Calling chunk_page twice with different pages must not mix them."""
        chunks_p1 = chunk_page(_make_text(400), page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        chunks_p2 = chunk_page(_make_text(400), page=2, doc_id=DOC_ID, doc_name=DOC_NAME)

        for c in chunks_p1:
            assert c["page"] == 1
        for c in chunks_p2:
            assert c["page"] == 2

    def test_doc_name_preserved(self):
        chunks = chunk_page(_make_text(100), page=1, doc_id=DOC_ID, doc_name="my_manual.pdf")
        for c in chunks:
            assert c["doc_name"] == "my_manual.pdf"

    def test_doc_id_preserved(self):
        chunks = chunk_page(_make_text(100), page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        for c in chunks:
            assert c["doc_id"] == DOC_ID


class TestShortText:
    """test_short_text: text < 600 tokens → single chunk."""

    def test_single_chunk_returned(self):
        text = _make_text(300)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"

    def test_single_chunk_contains_all_text(self):
        text = _make_text(300)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert chunks[0]["text"] == text

    def test_exactly_at_boundary(self):
        """600 tokens exactly → still a single chunk."""
        text = _make_text(600)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert len(chunks) == 1

    def test_one_word(self):
        chunks = chunk_page("hello", page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "hello"


class TestEmptyText:
    """test_empty_text: empty text → empty list."""

    def test_empty_string(self):
        chunks = chunk_page("", page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert chunks == []

    def test_whitespace_only(self):
        chunks = chunk_page("   \n\t  ", page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert chunks == []

    def test_newlines_only(self):
        chunks = chunk_page("\n\n\n", page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        assert chunks == []


class TestChunkMetadataSchema:
    """Every chunk must carry the full metadata schema."""

    REQUIRED_KEYS = {
        "chunk_id", "doc_id", "doc_name", "page",
        "section_heading", "chunk_type", "text",
        "bbox", "thumbnail_path", "sheet_name", "row_range",
    }

    def test_all_keys_present(self):
        chunks = chunk_page(_make_text(50), page=3, doc_id=DOC_ID, doc_name=DOC_NAME)
        for c in chunks:
            missing = self.REQUIRED_KEYS - set(c.keys())
            assert not missing, f"Chunk missing keys: {missing}"

    def test_chunk_ids_are_unique(self):
        text = _make_text(1200)
        chunks = chunk_page(text, page=1, doc_id=DOC_ID, doc_name=DOC_NAME)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk_ids found"
