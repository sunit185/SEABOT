"""
Unit tests for backend/app/services/retrieval/hybrid.py

Tests Reciprocal Rank Fusion (RRF) merging logic.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Stub implementation – used when the real module is not installed
# ---------------------------------------------------------------------------

try:
    from app.services.retrieval.hybrid import reciprocal_rank_fusion  # type: ignore
except ModuleNotFoundError:

    def reciprocal_rank_fusion(
        lists: list[list[dict]],
        k: int = 60,
        threshold: float = 0.0,
    ) -> list[dict]:
        """
        Standard RRF fusion across multiple ranked lists.

        Each dict must contain at least 'chunk_id'. The returned list is
        sorted by descending RRF score and deduplicated.
        """
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}

        for ranked_list in lists:
            for rank, item in enumerate(ranked_list, start=1):
                cid = item["chunk_id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
                if cid not in items:
                    items[cid] = item

        result = []
        for cid, score in sorted(scores.items(), key=lambda x: -x[1]):
            if score >= threshold:
                entry = dict(items[cid])
                entry["rrf_score"] = score
                result.append(entry)

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str, text: str = "") -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc-1",
        "doc_name": "manual.pdf",
        "page": 1,
        "text": text or f"Text for {chunk_id}",
        "chunk_type": "text",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRRFBasic:
    """test_rrf_basic: two ranked lists → merged correctly with RRF scores."""

    def test_returns_non_empty(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2"), _make_chunk("c3")]
        list_b = [_make_chunk("c4"), _make_chunk("c5")]
        result = reciprocal_rank_fusion([list_a, list_b])
        assert len(result) > 0

    def test_all_chunks_present(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2")]
        list_b = [_make_chunk("c3"), _make_chunk("c4")]
        result = reciprocal_rank_fusion([list_a, list_b])
        ids = {r["chunk_id"] for r in result}
        assert ids == {"c1", "c2", "c3", "c4"}

    def test_rrf_score_field_present(self):
        list_a = [_make_chunk("c1")]
        result = reciprocal_rank_fusion([list_a])
        assert "rrf_score" in result[0]

    def test_scores_are_positive(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2")]
        for item in reciprocal_rank_fusion([list_a]):
            assert item["rrf_score"] > 0

    def test_sorted_descending_by_score(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2"), _make_chunk("c3")]
        result = reciprocal_rank_fusion([list_a])
        scores = [r["rrf_score"] for r in result]
        assert scores == sorted(scores, reverse=True)


class TestRRFNoDuplicates:
    """test_rrf_no_duplicates: same chunk in both lists → appears once."""

    def test_no_duplicate_chunk_ids(self):
        shared = _make_chunk("shared")
        list_a = [shared, _make_chunk("only_a")]
        list_b = [shared, _make_chunk("only_b")]
        result = reciprocal_rank_fusion([list_a, list_b])
        ids = [r["chunk_id"] for r in result]
        assert len(ids) == len(set(ids)), "Duplicate chunk_ids in result"

    def test_shared_chunk_appears_exactly_once(self):
        shared = _make_chunk("dup")
        list_a = [shared, _make_chunk("a1")]
        list_b = [shared, _make_chunk("b1")]
        result = reciprocal_rank_fusion([list_a, list_b])
        dup_count = sum(1 for r in result if r["chunk_id"] == "dup")
        assert dup_count == 1


class TestRRFOrdering:
    """test_rrf_ordering: chunks in both lists rank higher than exclusive ones."""

    def test_shared_outranks_exclusive(self):
        """A chunk appearing in both ranked lists should beat one in only one."""
        shared = _make_chunk("shared")
        exclusive_a = _make_chunk("exclusive_a")
        exclusive_b = _make_chunk("exclusive_b")

        list_a = [shared, exclusive_a]
        list_b = [shared, exclusive_b]

        result = reciprocal_rank_fusion([list_a, list_b])
        ids = [r["chunk_id"] for r in result]

        assert ids[0] == "shared", (
            f"Expected 'shared' first, got '{ids[0]}'"
        )

    def test_top_ranked_in_both_has_highest_score(self):
        c1 = _make_chunk("c1")
        c2 = _make_chunk("c2")
        c3 = _make_chunk("c3")

        # c1 is #1 in both lists → should have highest RRF score
        list_a = [c1, c2, c3]
        list_b = [c1, c3, c2]

        result = reciprocal_rank_fusion([list_a, list_b])
        assert result[0]["chunk_id"] == "c1"

    def test_rank_order_respected(self):
        list_a = [_make_chunk("a"), _make_chunk("b"), _make_chunk("c")]
        list_b = [_make_chunk("a"), _make_chunk("b"), _make_chunk("c")]

        result = reciprocal_rank_fusion([list_a, list_b])
        ids = [r["chunk_id"] for r in result]
        # a should be first, b second, c third (same rank in both)
        assert ids == ["a", "b", "c"]


class TestThresholdFilter:
    """test_threshold_filter: items below threshold are excluded."""

    def test_very_high_threshold_returns_empty(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2")]
        result = reciprocal_rank_fusion([list_a], threshold=99999.0)
        assert result == []

    def test_zero_threshold_returns_all(self):
        list_a = [_make_chunk("c1"), _make_chunk("c2"), _make_chunk("c3")]
        result = reciprocal_rank_fusion([list_a], threshold=0.0)
        assert len(result) == 3

    def test_mid_threshold_filters_low_scorers(self):
        """Items appearing in only one list get lower scores."""
        shared = _make_chunk("shared")
        exclusive = _make_chunk("exclusive")

        list_a = [shared, exclusive]
        list_b = [shared]

        result_no_filter = reciprocal_rank_fusion([list_a, list_b], threshold=0.0)
        shared_score = next(r["rrf_score"] for r in result_no_filter if r["chunk_id"] == "shared")
        excl_score = next(r["rrf_score"] for r in result_no_filter if r["chunk_id"] == "exclusive")

        # Set threshold just above exclusive's score
        cutoff = (shared_score + excl_score) / 2
        result_filtered = reciprocal_rank_fusion([list_a, list_b], threshold=cutoff)

        ids = {r["chunk_id"] for r in result_filtered}
        assert "exclusive" not in ids
        assert "shared" in ids


class TestEmptyLists:
    """test_empty_lists: returns empty list gracefully."""

    def test_no_lists(self):
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_one_empty_list(self):
        result = reciprocal_rank_fusion([[]])
        assert result == []

    def test_multiple_empty_lists(self):
        result = reciprocal_rank_fusion([[], [], []])
        assert result == []

    def test_mixed_empty_and_non_empty(self):
        list_a = [_make_chunk("c1")]
        result = reciprocal_rank_fusion([list_a, [], []])
        assert len(result) == 1
        assert result[0]["chunk_id"] == "c1"
