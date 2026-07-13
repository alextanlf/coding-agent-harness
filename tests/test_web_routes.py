import pytest
from httpx import AsyncClient, ASGITransport
from web.app import create_app

@pytest.fixture
async def client(tmp_path):
    app = create_app(
        workspace_root=str(tmp_path),
        credential_path=str(tmp_path / "credentials.enc"),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_serves_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

@pytest.mark.asyncio
async def test_credential_status_not_configured(client):
    resp = await client.get("/api/credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False

@pytest.mark.asyncio
async def test_store_and_check_credentials(client):
    resp = await client.post("/api/credentials", json={
        "master_password": "testpass",
        "api_key": "sk-testkey123",
    })
    assert resp.status_code == 200
    resp = await client.get("/api/credentials")
    assert resp.json()["configured"] is True

@pytest.mark.asyncio
async def test_clear_credentials(client):
    await client.post("/api/credentials", json={
        "master_password": "pass",
        "api_key": "sk-test",
    })
    resp = await client.delete("/api/credentials")
    assert resp.status_code == 200
    resp = await client.get("/api/credentials")
    assert resp.json()["configured"] is False

@pytest.mark.asyncio
async def test_credential_status_never_leaks_key(client):
    await client.post("/api/credentials", json={
        "master_password": "pass",
        "api_key": "sk-supersecret",
    })
    resp = await client.get("/api/credentials")
    assert "sk-supersecret" not in resp.text
