"""
Health check router.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Chat
from app.services.llm import ollama_client
from app.services.retrieval import vector_store as vs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    settings = get_settings()

    # Check Ollama connectivity
    ollama_ok = False
    try:
        ollama_ok = await ollama_client.health_check()
    except Exception as exc:
        logger.warning("Ollama health check failed: %s", exc)

    # Count ChromaDB documents (chunks)
    chroma_docs = 0
    try:
        chroma_docs = vs.count()
    except Exception as exc:
        logger.warning("ChromaDB count failed: %s", exc)

    # Count chats in DB
    db_chats = 0
    try:
        result = await db.execute(select(func.count()).select_from(Chat))
        db_chats = result.scalar_one_or_none() or 0
    except Exception as exc:
        logger.warning("DB chat count failed: %s", exc)

    overall_status = "ok" if ollama_ok else "degraded"

    return {
        "status": overall_status,
        "ollama_connected": ollama_ok,
        "model": settings.OLLAMA_MODEL,
        "chroma_docs": chroma_docs,
        "db_chats": db_chats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
