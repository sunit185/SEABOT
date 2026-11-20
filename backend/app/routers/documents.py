"""Documents router: upload, list, status, and delete."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, async_session_factory
from app.models import Document
from app.schemas import DocumentResponse, DocumentStatus
from app.services.ingestion.pipeline import ingest_document
from app.services.llm import ollama_client
from app.services.retrieval import vector_store, bm25_index

logger = logging.getLogger("seabot.documents")

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".xlsx": "xlsx"}


async def _run_ingest_job(doc_id: str, file_path: str, file_type: str, file_name: str) -> None:
    settings = get_settings()
    async with async_session_factory() as db:
        await ingest_document(
            doc_id=doc_id,
            file_path=file_path,
            file_type=file_type,
            doc_name=file_name,
            settings=settings,
            db=db,
            ollama_client=ollama_client,
            vector_store=vector_store,
            bm25_index=bm25_index,
        )


@router.post("/upload", response_model=List[DocumentResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    from app.main import job_queue
    settings = get_settings()
    results: List[DocumentResponse] = []

    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file format '{ext}'. Only .pdf, .docx, and .xlsx are supported.",
            )

        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_MB:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_MB}MB.",
            )

        sha256 = hashlib.sha256(content).hexdigest()

        # Check for duplicates
        stmt = select(Document).where(Document.sha256 == sha256)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            results.append(DocumentResponse.model_validate(existing))
            continue

        doc_id = str(uuid.uuid4())
        file_type = ALLOWED_EXTENSIONS[ext]
        safe_name = Path(file.filename or "upload").name
        dest_dir = Path(settings.DATA_DIR) / "uploads" / doc_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_name

        with open(dest_path, "wb") as f:
            f.write(content)

        doc = Document(
            id=doc_id,
            name=safe_name,
            file_path=str(dest_path),
            sha256=sha256,
            file_type=file_type,
            status="uploading",
            size_bytes=len(content),
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Enqueue ingestion job
        await job_queue.enqueue(
            job_id=doc_id,
            coro_fn=_run_ingest_job,
            doc_id=doc_id,
            file_path=str(dest_path),
            file_type=file_type,
            file_name=safe_name,
        )

        results.append(DocumentResponse.model_validate(doc))

    return results


@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)) -> List[DocumentResponse]:
    stmt = select(Document).order_by(Document.created_at.desc())
    docs = (await db.execute(stmt)).scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}/status", response_model=DocumentStatus)
async def get_document_status(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatus:
    stmt = select(Document).where(Document.id == doc_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return DocumentStatus(id=doc.id, status=doc.status, error_msg=doc.error_msg)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    settings = get_settings()
    stmt = select(Document).where(Document.id == doc_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    # 1. Delete vector store chunks
    try:
        vector_store.delete_by_doc_id(doc_id)
    except Exception as e:
        logger.warning("Failed to delete vector store chunks for %s: %s", doc_id, e)

    # 2. Delete BM25 chunks
    try:
        bm25_index.delete_by_doc_id(doc_id)
    except Exception as e:
        logger.warning("Failed to delete BM25 chunks for %s: %s", doc_id, e)

    # 3. Delete files on disk
    upload_dir = Path(settings.DATA_DIR) / "uploads" / doc_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    thumb_dir = Path(settings.DATA_DIR) / "thumbnails" / doc_id
    if thumb_dir.exists():
        shutil.rmtree(thumb_dir, ignore_errors=True)

    # 4. Delete DB row
    await db.delete(doc)
    await db.commit()
