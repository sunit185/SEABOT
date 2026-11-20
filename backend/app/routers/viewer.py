"""
Viewer router: PDF page rendering and Excel sheet preview.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import openpyxl
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document
from app.config import get_settings
from app.services.retrieval import bm25_index as bm25_svc
from app.services.retrieval import vector_store as vs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viewer", tags=["viewer"])


# ---------------------------------------------------------------------------
# GET /api/viewer/{doc_id}/page/{page_num}
# ---------------------------------------------------------------------------
@router.get("/{doc_id}/page/{page_num}")
async def get_page(
    doc_id: str,
    page_num: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns a base64-encoded PNG of the requested PDF page plus chunk
    highlight metadata for that page.
    """
    settings = get_settings()

    # Load document record
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.file_path
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Open PDF and render page
    try:
        pdf = fitz.open(file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to open PDF: {exc}") from exc

    total_pages = len(pdf)

    if page_num < 1 or page_num > total_pages:
        raise HTTPException(
            status_code=422,
            detail=f"page_num must be between 1 and {total_pages}",
        )

    # Render at 150 dpi (72 dpi is native, so scale = 150/72 ≈ 2.08)
    scale = 150 / 72
    matrix = fitz.Matrix(scale, scale)
    page_obj = pdf[page_num - 1]
    pix = page_obj.get_pixmap(matrix=matrix)
    png_bytes = pix.tobytes("png")
    page_image_b64 = base64.b64encode(png_bytes).decode("utf-8")

    width = pix.width
    height = pix.height
    pdf.close()

    # Load chunks for this doc+page
    chunks = await _get_chunks_for_page(doc_id, page_num, settings)

    chunk_meta = []
    for c in chunks:
        bbox = c.get("bbox")
        # Scale bbox coordinates to match the rendered image resolution
        scaled_bbox = None
        if bbox:
            if isinstance(bbox, str):
                import json
                try:
                    bbox = json.loads(bbox)
                except Exception:
                    bbox = None
            if bbox and len(bbox) == 4:
                scaled_bbox = [coord * scale for coord in bbox]

        text = c.get("text", "")
        text_preview = text[:200] + "..." if len(text) > 200 else text

        chunk_meta.append(
            {
                "chunk_id": c.get("chunk_id", ""),
                "bbox": scaled_bbox,
                "text_preview": text_preview,
            }
        )

    return {
        "page_image_base64": page_image_b64,
        "width": width,
        "height": height,
        "page_num": page_num,
        "total_pages": total_pages,
        "chunks": chunk_meta,
    }


# ---------------------------------------------------------------------------
# GET /api/viewer/{doc_id}/sheet/{sheet_name}
# ---------------------------------------------------------------------------
@router.get("/{doc_id}/sheet/{sheet_name}")
async def get_sheet(
    doc_id: str,
    sheet_name: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return an Excel sheet as a markdown table string plus row count.
    """
    # Load document record
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.file_path
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    if doc.file_type not in ("xlsx", "xls", "excel"):
        raise HTTPException(
            status_code=422, detail="Document is not an Excel file"
        )

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to open Excel file: {exc}"
        ) from exc

    if sheet_name not in wb.sheetnames:
        raise HTTPException(
            status_code=404,
            detail=f"Sheet '{sheet_name}' not found. Available sheets: {wb.sheetnames}",
        )

    ws = wb[sheet_name]
    rows: List[List[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])

    wb.close()

    total_rows = len(rows)

    if not rows:
        return {
            "sheet_name": sheet_name,
            "content_markdown": "",
            "total_rows": 0,
        }

    # Build markdown table
    header = rows[0]
    separator = ["---"] * len(header)
    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for data_row in rows[1:]:
        # Escape pipe characters in cell values
        escaped = [cell.replace("|", "\\|") for cell in data_row]
        # Pad row to match header width
        while len(escaped) < len(header):
            escaped.append("")
        md_lines.append("| " + " | ".join(escaped) + " |")

    content_markdown = "\n".join(md_lines)

    return {
        "sheet_name": sheet_name,
        "content_markdown": content_markdown,
        "total_rows": total_rows,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_chunks_for_page(
    doc_id: str, page_num: int, settings
) -> List[Dict[str, Any]]:
    """
    Retrieve all indexed chunks for a specific doc+page.
    Tries ChromaDB metadata filter first, falls back to BM25 search.
    """
    chunks: List[Dict[str, Any]] = []

    # Try ChromaDB metadata filter
    try:
        collection = vs.get_collection()
        results = collection.get(
            where={"$and": [{"doc_id": doc_id}, {"page": page_num}]},
            include=["metadatas", "documents"],
        )
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])
        for i, cid in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            text = documents[i] if i < len(documents) else ""
            meta["chunk_id"] = cid
            meta["text"] = text
            chunks.append(meta)
        if chunks:
            return chunks
    except Exception as exc:
        logger.warning("ChromaDB page query failed: %s", exc)

    # Fallback: BM25 search with doc_id filter and page keyword
    try:
        bm25_results = bm25_svc.search(
            query=f"page:{page_num}",
            limit=50,
            doc_ids=[doc_id],
        )
        chunks = [
            r for r in bm25_results if r.get("page") == page_num
        ]
    except Exception as exc:
        logger.warning("BM25 page query failed: %s", exc)

    return chunks
