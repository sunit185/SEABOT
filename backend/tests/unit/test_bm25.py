"""Unit tests for SQLite FTS5 BM25 index."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from app.services.retrieval.bm25_index import BM25Index


@pytest.fixture
def temp_bm25(tmp_path: Path):
    db_file = tmp_path / "test_fts.db"
    index = BM25Index(db_path=str(db_file))
    index.init_fts()
    return index


def test_add_and_search(temp_bm25: BM25Index):
    chunks = [
        {
            "chunk_id": "c1",
            "doc_id": "d1",
            "text": "Emergency bilge pump operating procedure and valve alignment.",
        },
        {
            "chunk_id": "c2",
            "doc_id": "d1",
            "text": "Main engine cylinder head tightening torque is 1200 Nm.",
        },
        {
            "chunk_id": "c3",
            "doc_id": "d2",
            "text": "Fire damper release mechanism inspection checklist.",
        },
    ]
    temp_bm25.add_chunks(chunks)

    results = temp_bm25.search("bilge pump", limit=5)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "c1"


def test_search_no_results(temp_bm25: BM25Index):
    chunks = [
        {"chunk_id": "c1", "doc_id": "d1", "text": "Fuel oil purifier manual."},
    ]
    temp_bm25.add_chunks(chunks)
    results = temp_bm25.search("gyrocompass satellite navigation", limit=5)
    assert len(results) == 0


def test_delete_by_doc_id(temp_bm25: BM25Index):
    chunks = [
        {"chunk_id": "c1", "doc_id": "d1", "text": "Auxiliary boiler burner settings."},
        {"chunk_id": "c2", "doc_id": "d2", "text": "Auxiliary boiler feed water pump."},
    ]
    temp_bm25.add_chunks(chunks)

    # Delete d1
    temp_bm25.delete_by_doc_id("d1")

    res = temp_bm25.search("boiler", limit=5)
    assert len(res) == 1
    assert res[0]["doc_id"] == "d2"
