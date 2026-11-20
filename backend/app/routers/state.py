"""
State router: GET/PUT for user_state table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import UserState
from app.schemas import UserStateSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/state", tags=["state"])


# ---------------------------------------------------------------------------
# GET /api/state — return current user state
# ---------------------------------------------------------------------------
@router.get("", response_model=UserStateSchema)
async def get_state(db: AsyncSession = Depends(get_db)) -> UserStateSchema:
    state = await _get_or_create_state(db)
    return UserStateSchema.model_validate(state)


# ---------------------------------------------------------------------------
# PUT /api/state — upsert user state (partial update accepted)
# ---------------------------------------------------------------------------
@router.put("", response_model=UserStateSchema)
async def put_state(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> UserStateSchema:
    state = await _get_or_create_state(db)

    # Apply only the keys present in body (partial update)
    allowed_fields = {
        "active_chat_id",
        "sidebar_collapsed",
        "sidebar_scroll",
        "viewer_doc_id",
        "viewer_page",
        "input_draft",
    }

    for field, value in body.items():
        if field in allowed_fields:
            setattr(state, field, value)
        else:
            logger.debug("Ignoring unknown state field: %s", field)

    state.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(state)
    return UserStateSchema.model_validate(state)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_state(db: AsyncSession) -> UserState:
    """Get the singleton UserState row (id=1), creating it if absent."""
    result = await db.execute(select(UserState).where(UserState.id == 1))
    state = result.scalar_one_or_none()
    if state is None:
        state = UserState(
            id=1,
            active_chat_id=None,
            sidebar_collapsed=0,
            sidebar_scroll=0,
            viewer_doc_id=None,
            viewer_page=None,
            input_draft=None,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state
