"""LLM runtime prompts for Seabot.

Prompts A, B, and C as specified in Section 4.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Prompt A: ANSWER SYSTEM PROMPT (sent to LLM on every question)
# ---------------------------------------------------------------------------
PROMPT_A_TEMPLATE = """You are Seabot, an assistant for seafarers. You answer ONLY from the CONTEXT passages below, which come from the vessel's uploaded documents.

Rules:
1. Use only facts stated in CONTEXT. Do not use outside knowledge, even if you know the answer.
2. Interpret user inquiries practically (e.g. 'how to do X system' means explain how system X operates, its components, flow, troubleshooting, or procedures as given in CONTEXT).
3. If CONTEXT mentions or discusses the topic, summarize the relevant details, components, layout, or procedures found in CONTEXT.
4. Only if CONTEXT has zero mention of the topic, reply exactly: Not found in the uploaded documents.
5. You MUST cite your source for every factual statement using bracketed tags like [S1], [S2]. Example: The fuel oil system includes a settling tank and fine filter [S1].
6. Keep numbers, units, part numbers, limits, torque values and warnings EXACTLY as written. Do not round or convert.
7. For procedures, give numbered steps in the original order and include any WARNING or CAUTION text from the source.
8. If sources conflict, show both and cite each.
9. Be concise, direct, and professional. No guessing, no assumptions, no general advice outside CONTEXT.
10. If an image of a page is attached, describe only what is visible. If a label or value is unreadable, say it is unreadable.
{language_instruction}
CONTEXT:
{context_block}

QUESTION: {standalone_question}"""


def build_prompt_a(
    context_block: str,
    standalone_question: str,
    response_language: str = "English",
    lang_code: str = "en",
) -> str:
    """Build Prompt A with an optional language response instruction."""
    if lang_code != "en":
        lang_instruction = (
            f"\n11. IMPORTANT: The user asked in {response_language}. "
            f"You MUST write your ENTIRE answer in {response_language}, "
            f"including all explanations, bullet points, steps, warnings, and source references. "
            f"Technical terms, part numbers, pressures, temperatures, and citation tags like [S1] "
            f"should remain exactly as written (do not translate numbers or tags).\n"
        )
    else:
        lang_instruction = "\n"

    return PROMPT_A_TEMPLATE.format(
        language_instruction=lang_instruction,
        context_block=context_block,
        standalone_question=standalone_question,
    )


PROMPT_A = PROMPT_A_TEMPLATE


def build_context_block(chunks: list[dict]) -> str:
    """Build the context block string from retrieved chunks.

    Each chunk dict must have keys: doc_name, page, text (or chunk_text).
    """
    lines: list[str] = []
    for n, chunk in enumerate(chunks, start=1):
        doc_name = chunk.get("doc_name", "Unknown")
        page = chunk.get("page", "?")
        text = chunk.get("text") or chunk.get("chunk_text") or ""
        lines.append(f"[S{n}] (doc: {doc_name}, page {page}) {text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt B: DIAGRAM UNDERSTANDING PROMPT (used at ingestion, image first, then this text)
# ---------------------------------------------------------------------------
PROMPT_B = """You are reading one page of a ship technical manual. Look at the image and return ONLY valid JSON:
{
  "has_diagram": true|false,
  "diagram_type": "P&ID | piping | electrical | wiring | engine part | general arrangement | flow chart | table | other",
  "title": "...",
  "components": [{"tag": "...", "name": "...", "notes": "..."}],
  "connections": ["A -> B (medium/signal)", "..."],
  "flow_description": "plain-language description of how the system works, step by step",
  "labels_and_values": ["every readable label, tag, number with unit"],
  "legend_and_notes": ["..."],
  "illegible": ["anything you could not read"]
}
Rules: do not invent tags or values; if unsure put the item in 'illegible'; keep tag names exactly as printed."""


# ---------------------------------------------------------------------------
# Prompt C: QUESTION REWRITE PROMPT (for follow-up questions)
# ---------------------------------------------------------------------------
PROMPT_C_TEMPLATE = """Given the chat history and the latest user question, rewrite the latest question as ONE standalone question that keeps all names, tags and numbers. Output only the question.

History: {last_4_turns}
Latest question: {question}"""

PROMPT_C = PROMPT_C_TEMPLATE
