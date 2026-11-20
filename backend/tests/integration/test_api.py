"""Integration tests for FastAPI endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "ollama_connected" in data


@pytest.mark.asyncio
async def test_chat_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create chat
        create_res = await client.post("/api/chats", json={"title": "Test Chat"})
        assert create_res.status_code == 201
        chat_id = create_res.json()["id"]

        # 2. Get chat
        get_res = await client.get(f"/api/chats/{chat_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == chat_id

        # 3. Rename chat
        patch_res = await client.patch(f"/api/chats/{chat_id}", json={"title": "Renamed Chat"})
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Renamed Chat"

        # 4. List chats
        list_res = await client.get("/api/chats")
        assert list_res.status_code == 200
        assert any(c["id"] == chat_id for c in list_res.json()["today"])

        # 5. Delete chat
        del_res = await client.delete(f"/api/chats/{chat_id}")
        assert del_res.status_code == 200

        # 6. Verify deleted
        get_after = await client.get(f"/api/chats/{chat_id}")
        assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_user_state_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Update state
        put_res = await client.put(
            "/api/state",
            json={"sidebar_collapsed": 1, "input_draft": "Emergency stop"},
        )
        assert put_res.status_code == 200

        # Get state
        get_res = await client.get("/api/state")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["sidebar_collapsed"] == 1
        assert data["input_draft"] == "Emergency stop"


@pytest.mark.asyncio
async def test_upload_invalid_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"files": ("test.txt", b"plain text content", "text/plain")}
        res = await client.post("/api/documents/upload", files=files)
        assert res.status_code == 422
