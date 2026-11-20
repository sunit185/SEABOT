from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String, nullable=True)  # pdf|docx|xlsx
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="uploading"
    )  # uploading|parsing|indexing|ready|failed
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starter_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Relationships
    message_sources: Mapped[list["MessageSource"]] = relationship(
        "MessageSource", back_populates="document", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at"
    )


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    chat_id: Mapped[str] = mapped_column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_partial: Mapped[int] = mapped_column(Integer, default=0)
    interrupted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    sources: Mapped[list["MessageSource"]] = relationship(
        "MessageSource", back_populates="message", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# MessageSource
# ---------------------------------------------------------------------------

class MessageSource(Base):
    __tablename__ = "message_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    doc_id: Mapped[str | None] = mapped_column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    doc_name: Mapped[str | None] = mapped_column(String, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="sources")
    document: Mapped["Document | None"] = relationship("Document", back_populates="message_sources")


# ---------------------------------------------------------------------------
# UserState
# ---------------------------------------------------------------------------

class UserState(Base):
    __tablename__ = "user_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sidebar_collapsed: Mapped[int] = mapped_column(Integer, default=0)
    sidebar_scroll: Mapped[int] = mapped_column(Integer, default=0)
    viewer_doc_id: Mapped[str | None] = mapped_column(String, nullable=True)
    viewer_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
