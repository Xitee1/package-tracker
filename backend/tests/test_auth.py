import pytest


@pytest.mark.asyncio
async def test_setup_creates_admin(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_setup_only_works_once(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin2", "password": "pass123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["is_admin"] is True


@pytest.mark.asyncio
async def test_status_no_users(client):
    resp = await client.get("/api/v1/auth/status")
    assert resp.status_code == 200
    assert resp.json() == {"setup_completed": False}


@pytest.mark.asyncio
async def test_status_after_setup(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.get("/api/v1/auth/status")
    assert resp.status_code == 200
    assert resp.json() == {"setup_completed": True}
