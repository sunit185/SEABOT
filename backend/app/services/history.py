"""History service: Chat, Message, MessageSource, and AuditLog CRUD."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuditLog, Chat, Document, Message, MessageSource
from app.schemas import ChatResponse, GroupedChats


async def create_chat(db: AsyncSession, title: Optional[str] = None) -> Chat:
    chat = Chat(title=title)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_chat(db: AsyncSession, chat_id: str) -> Optional[Chat]:
    stmt = (
        select(Chat)
        .where(Chat.id == chat_id)
        .options(
            selectinload(Chat.messages).selectinload(Message.sources)
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_chats(db: AsyncSession) -> GroupedChats:
    # Query all chats along with message count
    stmt = (
        select(
            Chat,
            func.count(Message.id).label("msg_count"),
        )
        .outerjoin(Message, Message.chat_id == Chat.id)
        .group_by(Chat.id)
        .order_by(Chat.updated_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)

    today: List[ChatResponse] = []
    yesterday: List[ChatResponse] = []
    previous_7_days: List[ChatResponse] = []
    older: List[ChatResponse] = []

    for chat_obj, msg_count in rows:
        resp = ChatResponse(
            id=chat_obj.id,
            title=chat_obj.title,
            created_at=chat_obj.created_at,
            updated_at=chat_obj.updated_at,
            message_count=msg_count,
        )
        t = chat_obj.updated_at
        if t >= today_start:
            today.append(resp)
        elif t >= yesterday_start:
            yesterday.append(resp)
        elif t >= week_start:
            previous_7_days.append(resp)
        else:
            older.append(resp)

    return GroupedChats(
        today=today,
        yesterday=yesterday,
        previous_7_days=previous_7_days,
        older=older,
    )


async def delete_chat(db: AsyncSession, chat_id: str) -> bool:
    stmt = select(Chat).where(Chat.id == chat_id)
    chat = (await db.execute(stmt)).scalar_one_or_none()
    if not chat:
        return False
    await db.delete(chat)
    await db.commit()
    return True


async def rename_chat(db: AsyncSession, chat_id: str, title: str) -> Optional[Chat]:
    stmt = select(Chat).where(Chat.id == chat_id)
    chat = (await db.execute(stmt)).scalar_one_or_none()
    if not chat:
        return None
    chat.title = title
    chat.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(chat)
    return chat


async def add_message(
    db: AsyncSession,
    chat_id: str,
    role: str,
    content: str,
    is_partial: int = 0,
    interrupted: int = 0,
) -> Message:
    msg = Message(
        chat_id=chat_id,
        role=role,
        content=content,
        is_partial=is_partial,
        interrupted=interrupted,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def update_message(
    db: AsyncSession,
    message_id: str,
    content: str,
    is_partial: int = 0,
    interrupted: int = 0,
) -> Optional[Message]:
    stmt = select(Message).where(Message.id == message_id)
    msg = (await db.execute(stmt)).scalar_one_or_none()
    if not msg:
        return None
    msg.content = content
    msg.is_partial = is_partial
    msg.interrupted = interrupted
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, chat_id: str) -> List[Message]:
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .options(selectinload(Message.sources))
        .order_by(Message.created_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def add_message_sources(
    db: AsyncSession, message_id: str, sources: List[Dict[str, Any]]
) -> List[MessageSource]:
    added: List[MessageSource] = []
    for s in sources:
        ms = MessageSource(
            message_id=message_id,
            doc_id=s.get("doc_id"),
            doc_name=s.get("doc_name"),
            page=s.get("page"),
            chunk_id=s.get("chunk_id"),
            chunk_text=s.get("chunk_text"),
            bbox=s.get("bbox") if isinstance(s.get("bbox"), str) else json.dumps(s.get("bbox")),
        )
        db.add(ms)
        added.append(ms)
    await db.commit()
    return added


async def clear_chats_by_range(
    db: AsyncSession, range_str: str, delete_docs: bool = False
) -> Dict[str, int]:
    now = datetime.utcnow()
    cutoff: Optional[datetime] = None

    if range_str == "last_hour":
        cutoff = now - timedelta(hours=1)
    elif range_str == "today":
        cutoff = datetime(now.year, now.month, now.day)
    elif range_str == "last_7_days":
        cutoff = now - timedelta(days=7)
    elif range_str == "all":
        cutoff = None

    chat_stmt = select(Chat)
    if cutoff:
        chat_stmt = chat_stmt.where(Chat.created_at >= cutoff)
    chats_to_delete = (await db.execute(chat_stmt)).scalars().all()
    chat_ids = [c.id for c in chats_to_delete]

    chats_deleted = len(chat_ids)
    messages_deleted = 0
    docs_deleted = 0

    if chat_ids:
        # Count messages
        msg_stmt = select(func.count(Message.id)).where(Message.chat_id.in_(chat_ids))
        messages_deleted = (await db.execute(msg_stmt)).scalar_one() or 0

        # Delete chats (cascades to messages and sources)
        del_stmt = delete(Chat).where(Chat.id.in_(chat_ids))
        await db.execute(del_stmt)

    if delete_docs:
        doc_stmt = select(Document)
        if cutoff:
            doc_stmt = doc_stmt.where(Document.created_at >= cutoff)
        docs_to_delete = (await db.execute(doc_stmt)).scalars().all()
        docs_deleted = len(docs_to_delete)
        for d in docs_to_delete:
            await db.delete(d)

    await db.commit()

    # Log audit
    await log_audit(
        db,
        action="clear_history",
        details={
            "range": range_str,
            "cutoff": cutoff.isoformat() if cutoff else "none",
            "chats_deleted": chats_deleted,
            "messages_deleted": messages_deleted,
            "docs_deleted": docs_deleted,
        },
    )

    return {
        "chats_deleted": chats_deleted,
        "messages_deleted": messages_deleted,
        "documents_deleted": docs_deleted,
    }


async def log_audit(db: AsyncSession, action: str, details: Dict[str, Any]) -> AuditLog:
    entry = AuditLog(
        action=action,
        details=json.dumps(details),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_message_sources(db: AsyncSession, message_id: str) -> List[MessageSource]:
    stmt = (
        select(MessageSource)
        .where(MessageSource.message_id == message_id)
        .order_by(MessageSource.id.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


# Alias for backward compatibility
list_chats_grouped = list_chats

