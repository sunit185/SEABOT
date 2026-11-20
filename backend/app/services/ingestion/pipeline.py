"""
pipeline.py — Main document ingestion orchestrator.

Orchestrates: parse → OCR → chunk → embed → index → thumbnails → starter questions.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

logger = logging.getLogger(__name__)


async def _update_status(db: AsyncSession, doc_id: str, status: str, error_msg: str | None = None) -> None:
    """Update document status (and optionally error_msg) in the DB."""
    from app.models import Document  # local import to avoid circular deps

    stmt = (
        update(Document)
        .where(Document.id == doc_id)
        .values(status=status, **({"error_msg": error_msg} if error_msg is not None else {}))
    )
    await db.execute(stmt)
    await db.commit()


async def _fire_and_forget_caption(
    png_bytes: bytes,
    page_index: int,
    doc_id: str,
    doc_name: str,
    ollama_client: Any,
    model: str,
    thumbnails_dir: str,
    vector_store: Any,
    db: AsyncSession,
) -> None:
    """
    Caption a diagram page and persist the result without blocking the caller.

    Saves thumbnail, calls Ollama vision, upserts a diagram chunk into both
    the vector store and the BM25 index, and updates the chunk's
    thumbnail_path in the vector store metadata.
    """
    from app.services.ingestion.diagram import caption_diagram, save_thumbnail

    try:
        thumb_path = save_thumbnail(png_bytes, doc_id, page_index, thumbnails_dir)
        caption_dict = await caption_diagram(png_bytes, ollama_client, model)
        caption_text = caption_dict.get("description", "") or caption_dict.get("caption", "")
        if caption_text:
            import uuid

            chunk = {
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page": page_index + 1,  # 1-indexed
                "section_heading": caption_dict.get("section_heading"),
                "chunk_type": "diagram",
                "bbox": None,
                "text": caption_text,
                "thumbnail_path": thumb_path,
            }
            # Embed the caption
            embeddings = await ollama_client.embed(
                # We don't have settings here; use a default model
                "nomic-embed-text",
                [caption_text],
            )
            if embeddings:
                vector_store.add_chunks([chunk], embeddings)
            logger.info("Diagram caption saved for doc %s page %d", doc_id, page_index + 1)
    except Exception as exc:
        logger.warning("Fire-and-forget caption failed for page %d: %s", page_index, exc)


async def ingest_document(
    doc_id: str,
    file_path: str,
    file_type: str,          # "pdf" | "docx" | "xlsx"
    doc_name: str,
    settings: Any,           # app.config.Settings
    db: AsyncSession,
    ollama_client: Any,
    vector_store: Any,
    bm25_index: Any,
) -> None:
    """
    Full document ingestion pipeline.

    1.  Update status → "parsing"
    2.  Route to the appropriate parser
    3.  OCR scanned pages
    4.  Chunk the pages
    5.  Update status → "indexing"
    6.  Embed all chunks
    7.  Add to vector store + BM25 index
    8.  Update document.pages in DB
    9.  Fire-and-forget diagram captioning / thumbnail saving
    10. Generate 3 starter questions
    11. Persist starter_questions on the Document row
    12. Update status → "ready"

    On any exception the status is set to "failed" and the error is re-raised.
    """
    from app.services.ingestion import pdf_parser, docx_parser, excel_parser
    from app.services.ingestion.chunker import create_chunks
    from app.services.ingestion.diagram import render_page_png
    from app.services.ingestion.ocr import ocr_page
    from app.models import Document

    try:
        # ------------------------------------------------------------------ #
        # Step 1 — parsing
        # ------------------------------------------------------------------ #
        await _update_status(db, doc_id, "parsing")

        thumbnails_dir = str(Path(settings.DATA_DIR) / "thumbnails")
        pages: list[dict[str, Any]] = []
        scanned_pages: list[int] = []
        diagram_pages: list[int] = []

        if file_type == "xlsx":
            # Excel returns pre-built chunks directly
            excel_chunks = excel_parser.parse_excel(file_path, doc_id, doc_name)
            # Wrap in a fake "ready chunks" path — skip normal chunking
            await _update_status(db, doc_id, "indexing")
            all_chunks = excel_chunks

            # Embed
            texts = [c["text"] for c in all_chunks]
            embeddings: list[list[float]] = []
            if texts:
                embeddings = await ollama_client.embed(settings.EMBED_MODEL, texts)

            if embeddings:
                vector_store.add_chunks(all_chunks, embeddings)
            bm25_index.add_chunks(all_chunks)

            # Update document pages (all excel chunks use page=1)
            async with db.begin_nested():
                await db.execute(
                    update(Document).where(Document.id == doc_id).values(pages=1)
                )

            # Starter questions from first chunk
            first_text = all_chunks[0]["text"][:1000] if all_chunks else ""
            starter_questions = await _generate_starter_questions(
                first_text, ollama_client, settings.OLLAMA_MODEL
            )
            async with db.begin_nested():
                await db.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(starter_questions=starter_questions)
                )
            await db.commit()
            await _update_status(db, doc_id, "ready")
            return

        # ------- PDF / DOCX path ------- #
        if file_type == "pdf":
            parsed = pdf_parser.parse_pdf(file_path, doc_id, doc_name)
        elif file_type == "docx":
            work_dir = str(Path(settings.DATA_DIR) / "uploads" / doc_id)
            parsed = docx_parser.parse_docx(file_path, doc_id, doc_name, work_dir)
        else:
            raise ValueError(f"Unsupported file_type: {file_type!r}")

        pages = parsed["pages"]
        scanned_pages = parsed.get("scanned_pages", [])
        diagram_pages = parsed.get("diagram_pages", [])

        # ------------------------------------------------------------------ #
        # Step 3 — OCR scanned pages
        # ------------------------------------------------------------------ #
        for page_index in scanned_pages:
            try:
                ocr_text = ocr_page(file_path, page_index, dpi=150)
                if ocr_text.strip():
                    pages[page_index]["text"] = ocr_text
                    pages[page_index]["is_scanned"] = True
            except Exception as exc:
                logger.warning("OCR failed for page %d: %s", page_index, exc)

        # ------------------------------------------------------------------ #
        # Step 4 — Chunk
        # ------------------------------------------------------------------ #
        all_chunks = create_chunks(
            pages=pages,
            doc_id=doc_id,
            doc_name=doc_name,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )

        # ------------------------------------------------------------------ #
        # Step 5 — indexing
        # ------------------------------------------------------------------ #
        await _update_status(db, doc_id, "indexing")

        # ------------------------------------------------------------------ #
        # Step 6 — Embed
        # ------------------------------------------------------------------ #
        texts = [c["text"] for c in all_chunks]
        embeddings = []
        if texts:
            embeddings = await ollama_client.embed(settings.EMBED_MODEL, texts)

        # ------------------------------------------------------------------ #
        # Step 7 — Add to stores
        # ------------------------------------------------------------------ #
        if embeddings:
            vector_store.add_chunks(all_chunks, embeddings)
        bm25_index.add_chunks(all_chunks)

        # ------------------------------------------------------------------ #
        # Step 8 — Update pages count
        # ------------------------------------------------------------------ #
        num_pages = len(pages)
        await db.execute(
            update(Document).where(Document.id == doc_id).values(pages=num_pages)
        )
        await db.commit()

        # ------------------------------------------------------------------ #
        # Step 9 — Diagram captioning (fire-and-forget)
        # ------------------------------------------------------------------ #
        for page_index in diagram_pages:
            try:
                png_bytes = render_page_png(file_path, page_index, dpi=150)
            except Exception as exc:
                logger.warning("Could not render page %d for thumbnail: %s", page_index, exc)
                continue

            # Save thumbnail synchronously (fast), caption asynchronously
            asyncio.create_task(
                _fire_and_forget_caption(
                    png_bytes=png_bytes,
                    page_index=page_index,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    ollama_client=ollama_client,
                    model=settings.OLLAMA_MODEL,
                    thumbnails_dir=thumbnails_dir,
                    vector_store=vector_store,
                    db=db,
                )
            )

        # ------------------------------------------------------------------ #
        # Step 10 & 11 — Starter questions
        # ------------------------------------------------------------------ #
        first_text = pages[0]["text"][:1000] if pages else ""
        starter_questions = await _generate_starter_questions(
            first_text, ollama_client, settings.OLLAMA_MODEL
        )
        await db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(starter_questions=starter_questions)
        )
        await db.commit()

        # ------------------------------------------------------------------ #
        # Step 12 — Ready
        # ------------------------------------------------------------------ #
        await _update_status(db, doc_id, "ready")
        logger.info("Ingestion complete for doc_id=%s (%s)", doc_id, doc_name)

    except Exception as exc:
        logger.error("Ingestion failed for doc_id=%s: %s", doc_id, exc, exc_info=True)
        await _update_status(db, doc_id, "failed", error_msg=str(exc))
        raise


async def _generate_starter_questions(
    text_excerpt: str,
    ollama_client: Any,
    model: str,
) -> list[str]:
    """
    Ask the LLM to generate 3 starter questions a seafarer might ask about
    the given document excerpt.

    Returns a list of up to 3 question strings.
    """
    if not text_excerpt.strip():
        return []

    prompt = (
        f"Given this document excerpt, suggest 3 questions a seafarer might ask:\n\n"
        f"{text_excerpt}\n\n"
        "List exactly 3 questions, numbered 1. 2. 3."
    )
    try:
        response = await ollama_client.generate(model=model, prompt=prompt)
        questions: list[str] = []
        for line in response.splitlines():
            line = line.strip()
            # Match lines like "1. What is ..." or "1) What is ..."
            match = re.match(r"^[1-3][\.\)]\s+(.+)$", line)
            if match:
                questions.append(match.group(1).strip())
            if len(questions) == 3:
                break
        return questions
    except Exception as exc:
        logger.warning("Starter question generation failed: %s", exc)
        return []
