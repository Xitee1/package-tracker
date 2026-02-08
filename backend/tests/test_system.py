import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_can_access_system_status(client, admin_token):
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["workers"] == []
    assert data["total_workers"] == 0


@pytest.mark.asyncio
async def test_non_admin_gets_403(client, user_token):
    resp = await client.get("/api/v1/system/status", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_gets_401(client):
    resp = await client.get("/api/v1/system/status")
    assert resp.status_code in (401, 403)
