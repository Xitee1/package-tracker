import pytest
from httpx import AsyncClient


async def _create_admin_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_get_smtp_config_empty(client: AsyncClient):
    token = await _create_admin_token(client)
    resp = await client.get("/api/v1/admin/smtp", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_save_smtp_config(client: AsyncClient):
    token = await _create_admin_token(client)
    resp = await client.put(
        "/api/v1/admin/smtp",
        json={
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": True,
            "sender_address": "noreply@example.com",
            "sender_name": "Package Tracker",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["host"] == "smtp.example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_update_smtp_config_keeps_password(client: AsyncClient):
    token = await _create_admin_token(client)
    # Create initial config
    await client.put(
        "/api/v1/admin/smtp",
        json={
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": True,
            "sender_address": "noreply@example.com",
            "sender_name": "Package Tracker",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Update without password
    resp = await client.put(
        "/api/v1/admin/smtp",
        json={
            "host": "smtp2.example.com",
            "port": 465,
            "sender_address": "noreply@example.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["host"] == "smtp2.example.com"


@pytest.mark.asyncio
async def test_smtp_requires_admin(client: AsyncClient):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    admin_token = resp.json()["access_token"]

    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "password123"})
    user_token = resp.json()["access_token"]

    resp = await client.get("/api/v1/admin/smtp", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403
