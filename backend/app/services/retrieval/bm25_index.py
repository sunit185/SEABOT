"""SQLite FTS5-based BM25 keyword search index for Seabot."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


_initialized = False


def _fts_db_path() -> str:
    return get_settings().fts_db_path


def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection to the FTS database."""
    db_path = _fts_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_fts() -> None:
    """Create the FTS5 virtual table if it does not already exist."""
    global _initialized
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks
            USING fts5(
                chunk_id UNINDEXED,
                doc_id   UNINDEXED,
                text
            )
            """
        )
        conn.commit()
        _initialized = True
        logger.info("FTS5 table initialised at %s", _fts_db_path())
    finally:
        conn.close()


def _ensure_fts() -> None:
    global _initialized
    if not _initialized:
        init_fts()


def add_chunks(chunks: list[dict]) -> None:
    """Insert or replace chunks into the FTS5 index.

    Each chunk dict must have: chunk_id, doc_id, text (or chunk_text).
    """
    if not chunks:
        return

    _ensure_fts()

    rows: list[tuple[str, str, str]] = []
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        doc_id = chunk.get("doc_id", "")
        text = chunk.get("text") or chunk.get("chunk_text") or ""
        rows.append((chunk_id, doc_id, text))

    conn = _get_connection()
    try:
        # Delete existing entries for these chunk_ids first (upsert behaviour)
        chunk_ids = [r[0] for r in rows]
        placeholders = ",".join("?" * len(chunk_ids))
        conn.execute(
            f"DELETE FROM fts_chunks WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        )
        conn.executemany(
            "INSERT INTO fts_chunks(chunk_id, doc_id, text) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        logger.debug("Inserted %d chunks into FTS5 index.", len(rows))
    finally:
        conn.close()


def search(
    query: str,
    limit: int,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """BM25 keyword search over indexed chunks."""
    _ensure_fts()
    conn = _get_connection()
    try:
        # Tokenize query into alphanumeric words (skip special punctuation)
        import re
        words = [w for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', query) if len(w) >= 2]
        if not words:
            return []
        fts_query = " OR ".join(f'"{w}"' for w in words)

        if doc_ids:
            placeholders = ",".join("?" * len(doc_ids))
            sql = f"""
                SELECT chunk_id, doc_id, text,
                       bm25(fts_chunks) AS score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                  AND doc_id IN ({placeholders})
                ORDER BY score
                LIMIT ?
            """
            params: list[Any] = [fts_query] + list(doc_ids) + [limit]
        else:
            sql = """
                SELECT chunk_id, doc_id, text,
                       bm25(fts_chunks) AS score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY score
                LIMIT ?
            """
            params = [fts_query, limit]

        rows = conn.execute(sql, params).fetchall()
        results: list[dict] = []
        for row in rows:
            results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "doc_id": row["doc_id"],
                    "score": row["score"],
                    "text": row["text"],
                }
            )
        return results
    except sqlite3.OperationalError as exc:
        # FTS5 may throw if the query is malformed; return empty rather than crash.
        logger.warning("FTS5 search error (query=%r): %s", query, exc)
        return []
    finally:
        conn.close()


def delete_by_doc_id(doc_id: str) -> None:
    """Remove all indexed chunks for a given document."""
    _ensure_fts()
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM fts_chunks WHERE doc_id = ?", (doc_id,))
        conn.commit()
        logger.info("Deleted FTS5 entries for doc_id=%s", doc_id)
    finally:
        conn.close()
