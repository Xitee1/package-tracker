import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "pass123"},
    )
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "regular", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "regular", "password": "pass"},
    )
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_version_returns_version(client, admin_token):
    resp = await client.get("/api/v1/version", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_version_accessible_by_regular_user(client, user_token):
    resp = await client.get("/api/v1/version", headers=auth(user_token))
    assert resp.status_code == 200
    assert "version" in resp.json()


@pytest.mark.asyncio
async def test_version_unauthenticated(client):
    resp = await client.get("/api/v1/version")
    assert resp.status_code in (401, 403)
