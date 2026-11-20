"""ChromaDB persistent vector store for Seabot."""

from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_COLLECTION_NAME = "seabot_chunks"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(name: str = _COLLECTION_NAME) -> chromadb.Collection:
    """Return (creating if needed) the ChromaDB collection with cosine distance."""
    global _collection
    if _collection is None or _collection.name != name:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]] | None = None,
) -> None:
    """Upsert chunk embeddings and metadata into ChromaDB.

    Each chunk dict must have:
        chunk_id (str), and any metadata fields.
    Embeddings can be provided via the `embeddings` list or inside each chunk dict as `chunk["embedding"]`.
    """
    if not chunks:
        return

    collection = get_collection()

    ids: list[str] = []
    embed_list: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for idx, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        if embeddings is not None and idx < len(embeddings):
            emb = embeddings[idx]
        else:
            emb = chunk.get("embedding")

        if emb is None:
            continue

        text = chunk.get("text") or chunk.get("chunk_text") or ""

        # Build metadata — ChromaDB only accepts str/int/float/bool values
        meta: dict[str, Any] = {}
        for key in (
            "doc_id", "doc_name", "page", "section_heading",
            "chunk_type", "thumbnail_path", "sheet_name", "row_range",
        ):
            val = chunk.get(key)
            if val is not None:
                meta[key] = val

        # bbox must be a string in metadata
        bbox = chunk.get("bbox")
        if bbox is not None:
            import json
            meta["bbox"] = json.dumps(bbox) if not isinstance(bbox, str) else bbox

        ids.append(chunk_id)
        embed_list.append(emb)
        documents.append(text)
        metadatas.append(meta)

    if not ids:
        return

    collection.upsert(
        ids=ids,
        embeddings=embed_list,
        documents=documents,
        metadatas=metadatas,
    )
    logger.debug("Upserted %d chunks into ChromaDB.", len(ids))


def query(
    embedding: list[float],
    n_results: int,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """Query ChromaDB by embedding similarity.

    Args:
        embedding: Query embedding vector.
        n_results: Max results to return.
        doc_ids: Optional filter — only return chunks from these document IDs.

    Returns:
        List of dicts with keys: chunk_id, doc_id, doc_name, page, text,
        distance, and all other stored metadata.
    """
    collection = get_collection()

    where: dict | None = None
    if doc_ids:
        if len(doc_ids) == 1:
            where = {"doc_id": {"$eq": doc_ids[0]}}
        else:
            where = {"doc_id": {"$in": doc_ids}}

    kwargs: dict[str, Any] = {
        "query_embeddings": [embedding],
        "n_results": min(n_results, max(collection.count(), 1)),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    try:
        results = collection.query(**kwargs)
    except Exception as exc:
        logger.error("ChromaDB query error: %s", exc)
        return []

    hits: list[dict] = []
    ids_list = results.get("ids", [[]])[0]
    docs_list = results.get("documents", [[]])[0]
    metas_list = results.get("metadatas", [[]])[0]
    dists_list = results.get("distances", [[]])[0]

    for chunk_id, text, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
        hit: dict = dict(meta or {})
        hit["chunk_id"] = chunk_id
        hit["text"] = text
        hit["distance"] = dist
        # Cosine similarity = 1 - cosine distance
        hit["score"] = 1.0 - float(dist)
        hits.append(hit)

    return hits


def delete_by_doc_id(doc_id: str) -> None:
    """Delete all chunks belonging to a document from ChromaDB."""
    collection = get_collection()
    try:
        collection.delete(where={"doc_id": {"$eq": doc_id}})
        logger.info("Deleted ChromaDB chunks for doc_id=%s", doc_id)
    except Exception as exc:
        logger.error("Error deleting ChromaDB chunks for doc_id=%s: %s", doc_id, exc)


def count() -> int:
    """Return total number of chunks stored in ChromaDB."""
    try:
        return get_collection().count()
    except Exception:
        return 0
