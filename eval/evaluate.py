#!/usr/bin/env python3
"""
Seabot Benchmark Evaluation Runner.

Runs 30 standard Q&A pairs against the Seabot API:
- 20 Answerable questions (checks keyword presence and valid citations)
- 10 Unanswerable questions (checks exact NOT-FOUND compliance)
Outputs pass/fail breakdown, accuracy %, citation correctness %, and NOT-FOUND rate %.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

API_BASE = os.getenv("SEABOT_API_URL", "http://localhost:8000/api")
QA_PAIRS_PATH = Path(__file__).parent / "qa_pairs.json"


def run_benchmark():
    if not QA_PAIRS_PATH.exists():
        print(f"Error: {QA_PAIRS_PATH} not found.")
        sys.exit(1)

    with open(QA_PAIRS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs = data.get("pairs", [])
    print(f"\n========================================================")
    print(f"⚓ SEABOT BENCHMARK EVALUATION ({len(pairs)} questions)")
    print(f"========================================================\n")

    client = httpx.Client(base_url=API_BASE, timeout=60.0)

    # 1. Health check
    try:
        health = client.get("/health").json()
        print(f"Connected to Seabot backend: {health.get('status')}, Ollama: {health.get('model')}")
    except Exception as e:
        print(f"Failed to connect to Seabot API at {API_BASE}: {e}")
        print("Note: Run evaluate.py against an active backend server.")
        sys.exit(1)

    # 2. Create evaluation chat
    chat = client.post("/chats", json={"title": "Benchmark Run"}).json()
    chat_id = chat["id"]

    results = []
    answerable_correct = 0
    total_answerable = 0
    unanswerable_correct = 0
    total_unanswerable = 0
    citations_valid_count = 0
    total_cited = 0

    print("\nRunning test cases...")
    print(f"{'ID':<6} {'Type':<14} {'Status':<8} {'Citations':<10} {'Question':<45}")
    print("-" * 85)

    for item in pairs:
        qid = item["id"]
        qtext = item["question"]
        is_answerable = item.get("answerable", True)

        # Post query via SSE streaming
        full_answer = ""
        received_sources = []

        try:
            with client.stream("POST", f"/chats/{chat_id}/ask", json={"question": qtext}) as response:
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        try:
                            payload = json.loads(line[5:].strip())
                            if payload.get("type") == "token":
                                full_answer += payload.get("content", "")
                            elif payload.get("type") == "sources":
                                received_sources = payload.get("sources", [])
                        except Exception:
                            pass
        except Exception as e:
            full_answer = f"ERROR: {e}"

        # Evaluate Answer
        passed = False
        citations_ok = False
        is_not_found = "not found in the uploaded documents" in full_answer.lower()

        if is_answerable:
            total_answerable += 1
            expected = item.get("expected_answer_contains", [])
            matches = [term.lower() in full_answer.lower() for term in expected]
            # Match if at least one expected term is present and not falsely flagged as not found
            if any(matches) and not is_not_found:
                passed = True
                answerable_correct += 1

            # Check citations
            if received_sources and any(f"[S{i}]" in full_answer for i in range(1, 7)):
                citations_ok = True
                citations_valid_count += 1
            total_cited += 1

        else:
            total_unanswerable += 1
            if is_not_found:
                passed = True
                unanswerable_correct += 1
            citations_ok = len(received_sources) == 0

        status_str = "PASS" if passed else "FAIL"
        type_str = "Answerable" if is_answerable else "Trap / N/A"
        cite_str = "VALID" if citations_ok else "N/A" if not is_answerable else "MISSING"

        print(f"{qid:<6} {type_str:<14} {status_str:<8} {cite_str:<10} {qtext[:42]}...")

        results.append({
            "id": qid,
            "question": qtext,
            "answerable": is_answerable,
            "passed": passed,
            "citations_valid": citations_ok,
            "answer": full_answer[:150] + "..." if len(full_answer) > 150 else full_answer,
            "sources_count": len(received_sources),
        })

    # Summary Statistics
    acc_answerable = (answerable_correct / total_answerable * 100) if total_answerable else 0
    acc_unanswerable = (unanswerable_correct / total_unanswerable * 100) if total_unanswerable else 0
    acc_citations = (citations_valid_count / total_cited * 100) if total_cited else 0

    print("\n" + "=" * 55)
    print("📊 BENCHMARK SUMMARY RESULTS")
    print("=" * 55)
    print(f"Answerable Accuracy:    {answerable_correct}/{total_answerable} ({acc_answerable:.1f}%)  [Target: >= 90%]")
    print(f"NOT-FOUND Trap Rate:    {unanswerable_correct}/{total_unanswerable} ({acc_unanswerable:.1f}%) [Target: 100%]")
    print(f"Citation Correctness:   {citations_valid_count}/{total_cited} ({acc_citations:.1f}%)")
    print("=" * 55)

    # Save report
    out_file = Path(__file__).parent / f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "answerable_accuracy_pct": acc_answerable,
            "not_found_rate_pct": acc_unanswerable,
            "citation_validity_pct": acc_citations,
            "total_questions": len(pairs),
        },
        "results": results,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"Report written to: {out_file}\n")


if __name__ == "__main__":
    run_benchmark()
