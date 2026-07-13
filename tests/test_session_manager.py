# tests/test_session_manager.py
import pytest
import json
from httpx import AsyncClient, ASGITransport
from web.app import create_app
from web.session_manager import SessionManager

@pytest.fixture
async def client(tmp_path):
    app = create_app(
        workspace_root=str(tmp_path / "ws"),
        credential_path=str(tmp_path / "credentials.enc"),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_create_session(client):
    resp = await client.post("/api/session", json={"task": "write hello.py"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data

@pytest.mark.asyncio
async def test_session_status(client):
    resp = await client.post("/api/session", json={"task": "do something"})
    session_id = resp.json()["session_id"]
    resp = await client.get(f"/api/session/{session_id}")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_session_not_found(client):
    resp = await client.get("/api/session/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_session_manager_creates_workspace(tmp_path):
    sm = SessionManager(
        workspace_root=tmp_path / "ws",
        credential_path=tmp_path / "cred.enc",
    )
    session_id = await sm.create_session("test task")
    session = sm.get_session(session_id)
    assert session is not None
    assert session["status"] in ["pending", "running", "completed", "failed"]
