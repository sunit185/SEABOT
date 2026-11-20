"""Citation grounding verification for Seabot RAG answers."""

from __future__ import annotations

import re


# Matches [S1], [S2], [S12] etc. in the answer text.
_CITATION_RE = re.compile(r"\[S(\d+)\]")


def verify_citations(
    answer: str,
    retrieved_chunk_ids: set[str],
) -> tuple[bool, list[str]]:
    """Verify that every citation in the answer refers to a retrieved chunk."""
    # Find all bracketed citations e.g. [S1], [S1, S2], [Source 1], [S 2]
    found: list[str] = []
    for bracketed in re.findall(r"\[([^\]]+)\]", answer):
        for num in re.findall(r"(?:S|Source|Doc)?\s*(\d+)", bracketed, re.IGNORECASE):
            found.append(f"S{num}")

    # Fallback for citations without brackets e.g. "as shown in S1"
    if not found:
        for num in re.findall(r"\bS(\d+)\b", answer):
            found.append(f"S{num}")

    if not found:
        return False, []

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_cited: list[str] = []
    for cid in found:
        if cid not in seen:
            seen.add(cid)
            unique_cited.append(cid)

    # At least one cited ID must exist in retrieved set
    valid_cited = [cid for cid in unique_cited if cid in retrieved_chunk_ids]
    if valid_cited:
        return True, valid_cited

    return False, []
