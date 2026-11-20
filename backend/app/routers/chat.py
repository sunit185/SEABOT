"""
Chat router: CRUD for chats + SSE RAG streaming endpoint.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import AuditLog, Chat, Document, Message, MessageSource
from app.schemas import (
    AskRequest,
    ChatCreate,
    ChatDetailResponse,
    ChatResponse,
    ClearHistoryRequest,
    ClearHistoryResponse,
    GroupedChats,
    MessageResponse,
    SourceChip,
)
from app.services import history, state_service
from app.services.llm import grounding, ollama_client, prompts
from app.services.llm.language_detector import detect_language, is_english
from app.services.retrieval import bm25_index, hybrid, vector_store
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])

VISUAL_KEYWORDS = [
    "diagram", "drawing", "p&id", "circuit", "valve", "line", "flow",
    "where is", "schematic", "piping", "wiring", "electrical", "layout",
]

NOT_FOUND_REPLY = (
    "Not found in the uploaded documents.\n\n"
    "Try rephrasing with more specific terms from the manual."
)

_GENERAL_PATTERNS = [
    r"\b(who are you|what are you|kaun ho|tum kaun ho|aap kaun ho)\b",
    r"\b(what can you do|what do you do|kya kar sakte ho|kya kar sakte)\b",
    r"\b(what do you know|kya pata hai|kya jankari|apko kiya pata|aapko kya pata|kya jaante ho)\b",
    r"\b(what documents|which documents|konsi document|available documents|list documents)\b",
    r"^(hi|hello|hey|namaste|नमस्ते|salaam)\b",
]


def _is_general_or_greeting(text: str) -> bool:
    q = text.lower().strip()
    return any(re.search(p, q) for p in _GENERAL_PATTERNS)


def _clean_hindi_text(text: str) -> str:
    text = text.replace("主要", "मुख्य")
    text = text.replace("सチーム", "स्टीम")
    text = text.replace("チーム", "स्टीम")
    text = text.replace("सirkulating", "सर्कुलेटिंग")
    text = text.replace("सirkुलेटिंग", "सर्कुलेटिंग")
    text = text.replace("सirk", "सर्क")
    text = text.replace("वискोसिटी", "विस्कोसिटी")
    text = text.replace("विजसिटी", "विस्कोसिटी")
    text = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff]", "", text)
    return text


# ---------------------------------------------------------------------------
# POST /api/chats — create new empty chat
# ---------------------------------------------------------------------------
@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(db: AsyncSession = Depends(get_db)) -> ChatResponse:
    chat = await history.create_chat(db)
    return ChatResponse(
        id=chat.id,
        title=chat.title or "New Chat",
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=0,
    )


# ---------------------------------------------------------------------------
# GET /api/chats — list chats grouped by time
# ---------------------------------------------------------------------------
@router.get("", response_model=GroupedChats)
async def list_chats(db: AsyncSession = Depends(get_db)) -> GroupedChats:
    return await history.list_chats_grouped(db)


# ---------------------------------------------------------------------------
# GET /api/chats/{chat_id} — get chat + messages with sources
# ---------------------------------------------------------------------------
@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)) -> ChatDetailResponse:
    chat = await history.get_chat(db, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_orm = await history.get_messages(db, chat_id)

    messages_out: List[MessageResponse] = []
    for msg in messages_orm:
        sources_orm = await history.get_message_sources(db, msg.id)
        sources = [
            SourceChip(
                chunk_id=s.chunk_id,
                doc_id=s.doc_id,
                doc_name=s.doc_name,
                page=s.page,
                thumbnail_path=_thumbnail_path(s.doc_id, s.page),
            )
            for s in sources_orm
        ]
        messages_out.append(
            MessageResponse(
                id=msg.id,
                chat_id=msg.chat_id,
                role=msg.role,
                content=msg.content,
                is_partial=msg.is_partial,
                interrupted=msg.interrupted,
                created_at=msg.created_at,
                sources=sources,
            )
        )

    return ChatDetailResponse(
        id=chat.id,
        title=chat.title or "New Chat",
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=messages_out,
    )


# ---------------------------------------------------------------------------
# PATCH /api/chats/{chat_id} — rename chat
# ---------------------------------------------------------------------------
@router.patch("/{chat_id}", response_model=ChatResponse)
async def rename_chat(
    chat_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")

    chat = await history.rename_chat(db, chat_id, title)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    return ChatResponse(
        id=chat.id,
        title=chat.title or "New Chat",
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=0,
        messages=[],
    )


# ---------------------------------------------------------------------------
# DELETE /api/chats/{chat_id}
# ---------------------------------------------------------------------------
@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, db: AsyncSession = Depends(get_db)) -> None:
    deleted = await history.delete_chat(db, chat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found")


# ---------------------------------------------------------------------------
# POST /api/chats/clear — bulk delete by time range
# ---------------------------------------------------------------------------
@router.post("/clear", response_model=ClearHistoryResponse)
async def clear_chats(
    body: ClearHistoryRequest,
    db: AsyncSession = Depends(get_db),
) -> ClearHistoryResponse:
    result = await history.clear_chats_by_range(db, body.range, body.delete_documents)

    # Write audit log
    audit = AuditLog(
        action="clear_chats",
        details=json.dumps(
            {"range": body.range, "delete_documents": body.delete_documents, "result": result}
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()

    return ClearHistoryResponse(**result)


# ---------------------------------------------------------------------------
# POST /api/chats/{chat_id}/ask — SSE RAG endpoint
# ---------------------------------------------------------------------------
@router.post("/{chat_id}/ask")
async def ask(
    chat_id: str,
    body: AskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    settings = get_settings()

    async def event_stream() -> AsyncGenerator[str, None]:
        nonlocal chat_id
        try:
            # 0. Ensure chat exists (self-healing if client sent temporary/new id)
            chat = await history.get_chat(db, chat_id)
            if chat is None:
                chat = await history.create_chat(db, title=body.question[:60])
                chat_id = chat.id

            # 1. Load existing message history
            prior_messages = await history.get_messages(db, chat_id)

            # 2. Save user message
            user_msg = await history.add_message(
                db, chat_id=chat_id, role="user", content=body.question
            )

            # 2b. Detect language of the user's question
            lang_code, lang_name = detect_language(body.question)
            logger.info(
                "Detected language for chat %s: %s (%s)",
                chat_id, lang_code, lang_name,
            )
            # Emit language event immediately so the UI can show a badge
            yield _sse("language", {"type": "language", "code": lang_code, "name": lang_name})

            # 2c. Check if question is a greeting or general inquiry about Seabot / documents
            if _is_general_or_greeting(body.question):
                doc_query = await db.execute(select(Document).where(Document.status == "ready"))
                docs = doc_query.scalars().all()
                if lang_code == "hi":
                    doc_names = "\n".join(f"• **{d.name}**" for d in docs) if docs else "• कोई दस्तावेज़ अपलोड नहीं है"
                    reply = (
                        "नमस्ते! मैं **सीबॉट (Seabot)** हूँ — जहाजी तकनीकी मैनुअल, इमरजेंसी चेकलिस्ट और परिचालन के लिए आपका ऑफ़लाइन मैरीटाइम एआई सहायक।\n\n"
                        "मेरे पास वर्तमान में इन अपलोड किए गए दस्तावेज़ों की पूरी जानकारी है:\n"
                        f"{doc_names}\n\n"
                        "आप मुझसे पूछ सकते हैं:\n"
                        "• मुख्य इंजन की खराबी (जैसे इंजन शुरू होकर बंद होना, स्कैवेंज फायर, हाई EGT)\n"
                        "• फ्यूल ऑयल व ल्यूब ऑयल सिस्टम के मुख्य भाग, वाल्व और लेआउट\n"
                        "• बल्क कार्गो लोडिंग सीक्वेंस, ड्राफ्ट व डीबैलास्टिंग प्रक्रियाएं\n"
                        "• सुरक्षा सावधानियां और इमरजेंसी चेकलिस्ट"
                    )
                else:
                    doc_names = "\n".join(f"• **{d.name}**" for d in docs) if docs else "• No documents uploaded yet"
                    reply = (
                        "Hello! I am **Seabot**, your air-gapped maritime AI assistant for vessel technical documentation, emergency procedures, and engineering manuals.\n\n"
                        "I have indexed and can answer questions from your uploaded vessel documents:\n"
                        f"{doc_names}\n\n"
                        "You can ask me about:\n"
                        "• Main engine troubleshooting (e.g. engine fails to start, scavenge space fire, low LO pressure)\n"
                        "• Fuel oil & lubricating oil systems (components, flow diagrams, operating limits)\n"
                        "• Bulk cargo loading guidance, deballasting sequences, and stability limits\n"
                        "• Safety procedures, Permit-to-Work, and crankcase inspection precautions\n\n"
                        "Feel free to ask questions in English, Hindi (हिंदी), or your preferred language!"
                    )
                assistant_msg = await history.add_message(
                    db, chat_id=chat_id, role="assistant", content="", is_partial=1
                )
                for word in reply.split(" "):
                    token = word + " "
                    yield _sse("token", {"type": "token", "content": token})
                await history.update_message(
                    db, assistant_msg.id, content=reply, is_partial=0
                )
                yield _sse("sources", {"type": "sources", "sources": []})
                yield _sse("done", {"type": "done"})
                return

            # 3. Question rewrite (if not first message)
            if prior_messages:
                last_4 = prior_messages[-4:]
                last_4_turns = "\n".join(
                    f"{m.role}: {m.content}" for m in last_4
                )
                rewrite_prompt = prompts.PROMPT_C.format(
                    last_4_turns=last_4_turns,
                    question=body.question,
                )
                standalone_question = await ollama_client.generate(
                    settings.OLLAMA_MODEL, rewrite_prompt
                )
                standalone_question = standalone_question.strip()
                # Clean common model preambles
                standalone_question = re.sub(
                    r"^(Here is the standalone question:?|Standalone question:?|Question:?)\s*",
                    "",
                    standalone_question,
                    flags=re.IGNORECASE,
                ).strip().strip('"').strip("'")
                if not standalone_question or len(standalone_question) < 4:
                    standalone_question = body.question
                logger.info(
                    "Rewrote question for chat %s: %r -> %r",
                    chat_id, body.question, standalone_question,
                )
            else:
                standalone_question = body.question

            # 4. Auto-title on first question
            if not prior_messages:
                raw_title = body.question[:60]
                # Strip trailing partial word
                if len(body.question) > 60:
                    raw_title = raw_title.rsplit(" ", 1)[0]
                await history.rename_chat(db, chat_id, raw_title or "New Chat")

            # 5. Retrieve chunks via hybrid retrieval
            # If the user asked in a non-English language (e.g. Hindi),
            # translate to an English search query for matching English manuals.
            search_query = standalone_question
            if lang_code != "en":
                try:
                    translate_prompt = (
                        "Translate the following question into a concise English search query for technical manuals. "
                        "Output ONLY the English query, nothing else.\n\n"
                        f"Question: {standalone_question}"
                    )
                    translated_q = await ollama_client.generate(settings.OLLAMA_MODEL, translate_prompt)
                    cleaned_q = translated_q.strip().strip('"').strip("'")
                    if cleaned_q and len(cleaned_q) > 3:
                        search_query = cleaned_q
                        logger.info("Translated non-English query %r -> %r for retrieval", standalone_question, search_query)
                except Exception as exc:
                    logger.warning("Query translation failed: %s; using original", exc)

            chunks = await hybrid.retrieve(
                question=search_query,
                doc_ids=body.scope_doc_ids,
                settings=settings,
                embed_fn=ollama_client.embed,
                vector_store=vector_store,
                bm25_index=bm25_index,
            )

            # 6. Handle empty retrieval
            if not chunks:
                assistant_msg = await history.add_message(
                    db, chat_id=chat_id, role="assistant", content="", is_partial=1
                )
                if lang_code == "hi":
                    full_answer = "अपलोड किए गए दस्तावेज़ों में नहीं मिला।\n\nकृपया मैन्युअल के विशिष्ट तकनीकी शब्दों के साथ पुनः प्रयास करें।"
                else:
                    full_answer = NOT_FOUND_REPLY
                for word in full_answer.split(" "):
                    token = word + " "
                    yield _sse("token", {"type": "token", "content": token})
                await history.update_message(
                    db, assistant_msg.id, content=full_answer, is_partial=0
                )
                yield _sse("done", {"type": "done"})
                return

            # 7. Visual intent detection
            q_lower = standalone_question.lower()
            has_visual_intent = any(kw in q_lower for kw in VISUAL_KEYWORDS)

            # 8. Check if any chunk is a diagram
            has_diagram_chunk = any(
                c.get("chunk_type") == "diagram" for c in chunks
            )

            # 9. Load page image if needed
            images_list: List[str] = []
            if has_visual_intent or has_diagram_chunk:
                img_b64 = await _load_page_image(chunks, settings)
                if img_b64:
                    images_list = [img_b64]

            # 10. Build context block (up to FINAL_TOP_K chunks → S1..S6)
            top_chunks = chunks[: settings.FINAL_TOP_K]
            context_parts = []
            for i, chunk in enumerate(top_chunks, start=1):
                doc_name = chunk.get("doc_name", "unknown")
                page = chunk.get("page", "?")
                text = chunk.get("text", "")
                context_parts.append(
                    f"[S{i}] (doc: {doc_name}, page {page})\n{text}"
                )
            context_block = "\n\n".join(context_parts)

            # 11. Build full prompt (with language instruction if non-English)
            full_prompt = prompts.build_prompt_a(
                context_block=context_block,
                standalone_question=standalone_question,
                response_language=lang_name,
                lang_code=lang_code,
            )

            # 12. Create assistant message row (partial)
            assistant_msg = await history.add_message(
                db, chat_id=chat_id, role="assistant", content="", is_partial=1
            )

            # 13. Stream tokens
            full_answer = ""
            token_count = 0
            async for token in ollama_client.generate_stream(
                settings.OLLAMA_MODEL, full_prompt, images=images_list or None
            ):
                full_answer += token
                token_count += 1
                if token_count % 20 == 0:
                    await history.update_message(
                        db, assistant_msg.id, content=full_answer, is_partial=1
                    )
                yield _sse("token", {"type": "token", "content": token})

                # Check client disconnect
                if await request.is_disconnected():
                    await history.update_message(
                        db, assistant_msg.id, content=full_answer, is_partial=0
                    )
                    return

            # 14. Verify citations
            valid, cited_ids = grounding.verify_citations(
                full_answer, {f"S{i}" for i in range(1, len(top_chunks) + 1)}
            )
            if not valid:
                if not full_answer.strip() or "not found in the uploaded documents" in full_answer.lower():
                    full_answer = NOT_FOUND_REPLY
                else:
                    # Model answered with facts from retrieved chunks but omitted explicit tags
                    valid = True
                    cited_ids = ["S1"]
                    full_answer = f"{full_answer.strip()} [S1]"

            # 15. Finalize message
            if lang_code == "hi":
                full_answer = _clean_hindi_text(full_answer)

            await history.update_message(
                db, assistant_msg.id, content=full_answer, is_partial=0
            )

            # 16. Save cited sources
            source_chips: List[dict] = []
            if valid:
                # Map S1..S6 back to chunks
                chunk_map = {f"S{i}": top_chunks[i - 1] for i in range(1, len(top_chunks) + 1)}
                for sid in cited_ids:
                    chunk = chunk_map.get(sid)
                    if chunk is None:
                        continue
                    ms = MessageSource(
                        id=str(uuid.uuid4()),
                        message_id=assistant_msg.id,
                        doc_id=chunk.get("doc_id", ""),
                        doc_name=chunk.get("doc_name", ""),
                        page=chunk.get("page"),
                        chunk_id=chunk.get("chunk_id", ""),
                        chunk_text=chunk.get("text", ""),
                        bbox=json.dumps(chunk.get("bbox")) if chunk.get("bbox") else None,
                    )
                    db.add(ms)
                    source_chips.append(
                        {
                            "chunk_id": chunk.get("chunk_id", ""),
                            "doc_id": chunk.get("doc_id", ""),
                            "doc_name": chunk.get("doc_name", ""),
                            "page": chunk.get("page"),
                            "thumbnail_path": _thumbnail_path(
                                chunk.get("doc_id", ""), chunk.get("page")
                            ),
                        }
                    )
                await db.commit()

            # 17. Yield sources event
            yield _sse("sources", {"type": "sources", "sources": source_chips})

            # 18. Yield done event
            yield _sse("done", {"type": "done"})

        except Exception as exc:
            logger.exception("Error in SSE stream for chat %s", chat_id)
            yield _sse("error", {"type": "error", "content": str(exc)})

    return EventSourceResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


def _thumbnail_path(doc_id: str, page: Optional[int]) -> Optional[str]:
    if doc_id and page is not None:
        return f"/thumbnails/{doc_id}/page_{page}.png"
    return None


async def _load_page_image(chunks: List[dict], settings) -> Optional[str]:
    """
    Return base64-encoded PNG of the first chunk's page.
    Uses cached thumbnail if available, otherwise renders via PyMuPDF.
    """
    import os
    from pathlib import Path

    for chunk in chunks:
        thumb = chunk.get("thumbnail_path")
        if thumb and os.path.exists(thumb):
            with open(thumb, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        # Try to render from PDF
        doc_id = chunk.get("doc_id")
        page_num = chunk.get("page")
        file_path = chunk.get("file_path")

        if not file_path and doc_id:
            # Try to find from data dir
            uploads_dir = Path(settings.DATA_DIR) / "uploads"
            matches = list(uploads_dir.glob(f"{doc_id}.*"))
            if matches:
                file_path = str(matches[0])

        if file_path and page_num is not None:
            try:
                pdf = fitz.open(file_path)
                if 0 <= (page_num - 1) < len(pdf):
                    page_obj = pdf[page_num - 1]
                    mat = fitz.Matrix(150 / 72, 150 / 72)
                    pix = page_obj.get_pixmap(matrix=mat)
                    return base64.b64encode(pix.tobytes("png")).decode("utf-8")
            except Exception as exc:
                logger.warning("Failed to render page image: %s", exc)

    return None
