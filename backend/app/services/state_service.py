"""State service: persistent user UI state."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserState


async def get_user_state(db: AsyncSession) -> UserState:
    stmt = select(UserState).where(UserState.id == 1)
    state = (await db.execute(stmt)).scalar_one_or_none()
    if not state:
        state = UserState(id=1)
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def save_user_state(db: AsyncSession, **kwargs: Any) -> UserState:
    state = await get_user_state(db)
    allowed_fields = {
        "active_chat_id",
        "sidebar_collapsed",
        "sidebar_scroll",
        "viewer_doc_id",
        "viewer_page",
        "input_draft",
    }
    for k, v in kwargs.items():
        if k in allowed_fields:
            setattr(state, k, v)
    state.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(state)
    return state
