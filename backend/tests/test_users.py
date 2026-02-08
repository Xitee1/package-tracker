import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_user(client, admin_token):
    resp = await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    assert resp.status_code == 201
    assert resp.json()["username"] == "user1"
    assert resp.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_list_users(client, admin_token):
    await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    resp = await client.get("/api/v1/users", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(client, admin_token):
    resp = await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    user_token = login.json()["access_token"]
    resp = await client.post("/api/v1/users", json={"username": "user2", "password": "pass"}, headers=auth(user_token))
    assert resp.status_code == 403
