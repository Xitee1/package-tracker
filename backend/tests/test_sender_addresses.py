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


@pytest.fixture
async def user2_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user2", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user2", "password": "pass"})
    return login.json()["access_token"]


@pytest.fixture(autouse=True)
async def enable_global_module(client, admin_token):
    """Enable the email-global module so sender-address endpoints are accessible."""
    await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_empty(client, user_token):
    resp = await client.get("/api/v1/providers/email-global/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_and_list(client, user_token):
    resp = await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email_address"] == "me@example.com"

    resp = await client.get("/api/v1/providers/email-global/sender-addresses", headers=auth(user_token))
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_same_user(client, user_token):
    await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    resp = await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_different_user(client, user_token, user2_token):
    await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "shared@example.com"},
        headers=auth(user_token),
    )
    resp = await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "shared@example.com"},
        headers=auth(user2_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete(client, user_token):
    resp = await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "del@example.com"},
        headers=auth(user_token),
    )
    addr_id = resp.json()["id"]
    resp = await client.delete(f"/api/v1/providers/email-global/sender-addresses/{addr_id}", headers=auth(user_token))
    assert resp.status_code == 204

    resp = await client.get("/api/v1/providers/email-global/sender-addresses", headers=auth(user_token))
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_other_users_address(client, user_token, user2_token):
    resp = await client.post(
        "/api/v1/providers/email-global/sender-addresses",
        json={"email_address": "other@example.com"},
        headers=auth(user_token),
    )
    addr_id = resp.json()["id"]
    resp = await client.delete(f"/api/v1/providers/email-global/sender-addresses/{addr_id}", headers=auth(user2_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_denied(client):
    resp = await client.get("/api/v1/providers/email-global/sender-addresses")
    assert resp.status_code in (401, 403)
