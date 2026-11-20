from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared / small schemas
# ---------------------------------------------------------------------------

class SourceChip(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str | None = None
    doc_id: str | None = None
    doc_name: str | None = None
    page: int | None = None
    chunk_text: str | None = None
    bbox: str | None = None           # JSON string "[x0,y0,x1,y1]"
    thumbnail_path: str | None = None


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------

class DocumentStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    error_msg: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    file_type: str | None = None
    pages: int | None = None
    status: str
    error_msg: str | None = None
    size_bytes: int | None = None
    created_at: datetime
    starter_questions: list[str] | None = None

    @field_validator("starter_questions", mode="before")
    @classmethod
    def parse_starter_questions(cls, v: Any) -> list[str]:
        if not v:
            return []
        while isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                break
        if isinstance(v, list):
            return [str(q) for q in v]
        return []


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------

class ChatCreate(BaseModel):
    title: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    role: str
    content: str
    is_partial: int = 0
    interrupted: int = 0
    created_at: datetime
    sources: list[SourceChip] = Field(default_factory=list)


class ChatDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)


class GroupedChats(BaseModel):
    today: list[ChatResponse] = Field(default_factory=list)
    yesterday: list[ChatResponse] = Field(default_factory=list)
    previous_7_days: list[ChatResponse] = Field(default_factory=list)
    older: list[ChatResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ask / RAG schemas
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    scope_doc_ids: list[str] | None = None


class AskResponse(BaseModel):
    """Used for non-streaming fallback; primary path uses SSE."""
    answer: str
    sources: list[SourceChip] = Field(default_factory=list)
    chat_id: str
    message_id: str


# ---------------------------------------------------------------------------
# Clear history schemas
# ---------------------------------------------------------------------------

class ClearHistoryRequest(BaseModel):
    range: Literal["last_hour", "today", "last_7_days", "all"]
    delete_documents: bool = False


class ClearHistoryResponse(BaseModel):
    chats_deleted: int = 0
    messages_deleted: int = 0
    documents_deleted: int = 0


# ---------------------------------------------------------------------------
# UserState schemas
# ---------------------------------------------------------------------------

class UserStateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    active_chat_id: str | None = None
    sidebar_collapsed: int = 0
    sidebar_scroll: int = 0
    viewer_doc_id: str | None = None
    viewer_page: int | None = None
    input_draft: str | None = None
    updated_at: datetime | None = None


class UserStateUpdate(BaseModel):
    """Partial update — all fields optional."""
    active_chat_id: str | None = None
    sidebar_collapsed: int | None = None
    sidebar_scroll: int | None = None
    viewer_doc_id: str | None = None
    viewer_page: int | None = None
    input_draft: str | None = None


# ---------------------------------------------------------------------------
# Health schema
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ollama_connected: bool
    model: str
    chroma_docs: int
    db_chats: int
    timestamp: datetime
