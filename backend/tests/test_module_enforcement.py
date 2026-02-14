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
async def test_accounts_blocked_when_imap_disabled(client, admin_token, user_token):
    # Disable email-imap module
    await client.put(
        "/api/v1/modules/email-imap",
        json={"enabled": False},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/accounts", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_accounts_allowed_when_imap_enabled(client, admin_token, user_token):
    # Ensure module is enabled (default)
    await client.put(
        "/api/v1/modules/email-imap",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/accounts", headers=auth(user_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sender_addresses_blocked_when_global_disabled(client, admin_token, user_token):
    # Trigger module initialization so email-global row exists (disabled by default)
    await client.get("/api/v1/modules", headers=auth(admin_token))
    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sender_addresses_allowed_when_global_enabled(client, admin_token, user_token):
    await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 200
