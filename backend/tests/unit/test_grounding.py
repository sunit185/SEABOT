"""Unit tests for citation grounding verification."""
from __future__ import annotations

import pytest
from app.services.llm.grounding import verify_citations


def test_valid_citations():
    answer = "The fuel oil service pump pressure should be 4.5 bar [S1]. Keep the valve open [S2]."
    retrieved = {"S1", "S2", "S3"}
    valid, cited = verify_citations(answer, retrieved)
    assert valid is True
    assert set(cited) == {"S1", "S2"}


def test_invalid_citation():
    answer = "Lubricating oil pressure must be 3.0 bar [S5]."
    retrieved = {"S1", "S2"}
    valid, cited = verify_citations(answer, retrieved)
    assert valid is False
    assert cited == []


def test_no_citations():
    answer = "The engine speed should be reduced immediately."
    retrieved = {"S1", "S2"}
    valid, cited = verify_citations(answer, retrieved)
    assert valid is False
    assert cited == []


def test_mixed_valid_and_invalid():
    answer = "First step is here [S1], second step is there [S7]."
    retrieved = {"S1", "S2"}
    valid, cited = verify_citations(answer, retrieved)
    assert valid is False
    assert cited == []


def test_multiple_citations_on_single_sentence():
    answer = "Both valves V101 and V102 must be locked [S1][S2]."
    retrieved = {"S1", "S2", "S3"}
    valid, cited = verify_citations(answer, retrieved)
    assert valid is True
    assert set(cited) == {"S1", "S2"}
