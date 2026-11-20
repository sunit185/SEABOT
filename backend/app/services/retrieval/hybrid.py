"""Hybrid retrieval (vector + BM25 → RRF fusion) for Seabot."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """Standard Reciprocal Rank Fusion over multiple ranked lists.

    Args:
        lists: Each sub-list is a ranked list of dicts. The dicts must contain
               a "chunk_id" key used to identify items across lists.
        k: RRF constant (default 60 as per the original paper).

    Returns:
        Merged list of dicts sorted by RRF score descending (highest first).
        Each dict has an added "rrf_score" key.
    """
    # Accumulate RRF scores per chunk_id
    rrf_scores: dict[str, float] = defaultdict(float)
    # Keep one copy of each chunk's metadata for the output
    chunk_data: dict[str, dict] = {}

    for ranked_list in lists:
        for rank, item in enumerate(ranked_list, start=1):
            cid = item.get("chunk_id")
            if not cid:
                continue
            rrf_scores[cid] += 1.0 / (k + rank)
            if cid not in chunk_data:
                chunk_data[cid] = item

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    result: list[dict] = []
    for cid in sorted_ids:
        entry = dict(chunk_data[cid])
        entry["rrf_score"] = rrf_scores[cid]
        result.append(entry)

    return result


# ---------------------------------------------------------------------------
# Main hybrid retrieve function
# ---------------------------------------------------------------------------

async def retrieve(
    question: str,
    doc_ids: list[str] | None,
    settings: Any,
    embed_fn: Callable[[str, list[str]], Coroutine[Any, Any, list[list[float]]]],
    vector_store: Any,
    bm25_index: Any,
) -> list[dict]:
    """Hybrid retrieval: embed → vector search + BM25 → RRF → filter → top-K.

    Args:
        question: User question (possibly rewritten as standalone).
        doc_ids: Optional list of doc IDs to scope the search.
        settings: App settings object (provides VECTOR_TOP_K, BM25_TOP_K,
                  FINAL_TOP_K, RELEVANCE_THRESHOLD, EMBED_MODEL).
        embed_fn: Async callable matching ollama_client.embed signature.
        vector_store: Module / object with a .query() method.
        bm25_index: Module / object with a .search() method.

    Returns:
        List of chunk dicts (up to FINAL_TOP_K) sorted by RRF score, with
        all original metadata preserved.
    """
    # 1. Embed the question
    try:
        embedding_list = await embed_fn(settings.EMBED_MODEL, [question])
        query_embedding: list[float] = embedding_list[0]
    except Exception as exc:
        logger.error("Embedding failed during retrieval: %s", exc)
        return []

    # 2. Vector search
    vector_results: list[dict] = []
    try:
        vector_results = vector_store.query(
            embedding=query_embedding,
            n_results=settings.VECTOR_TOP_K,
            doc_ids=doc_ids,
        )
    except Exception as exc:
        logger.error("Vector store query failed: %s", exc)

    # 3. BM25 search
    bm25_results: list[dict] = []
    try:
        bm25_hits = bm25_index.search(
            query=question,
            limit=settings.BM25_TOP_K,
            doc_ids=doc_ids,
        )
        # Enrich BM25 hits with vector metadata where available (best-effort)
        vec_by_id = {r["chunk_id"]: r for r in vector_results}
        for hit in bm25_hits:
            cid = hit.get("chunk_id")
            if cid and cid in vec_by_id:
                enriched = dict(vec_by_id[cid])
                enriched["score"] = hit["score"]  # keep BM25 score for reference
                bm25_results.append(enriched)
            else:
                bm25_results.append(hit)
    except Exception as exc:
        logger.error("BM25 search failed: %s", exc)

    # 4. RRF fusion
    fused = reciprocal_rank_fusion([vector_results, bm25_results])

    if not fused:
        return []

    # 5. Relevance filter using normalised RRF rank score.
    # The highest-ranked item gets score 1.0; others are relative.
    max_rrf = fused[0]["rrf_score"]
    threshold = settings.RELEVANCE_THRESHOLD

    filtered: list[dict] = []
    for item in fused:
        normalised = item["rrf_score"] / max_rrf if max_rrf > 0 else 0.0
        if normalised >= threshold:
            item["normalised_rrf"] = normalised
            filtered.append(item)

    # 6. Return top FINAL_TOP_K
    return filtered[: settings.FINAL_TOP_K]
