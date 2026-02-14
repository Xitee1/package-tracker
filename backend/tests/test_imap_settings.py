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
async def test_get_returns_defaults_when_no_row(client, admin_token):
    resp = await client.get("/api/v1/settings/imap", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_email_age_days"] == 7
    assert data["processing_delay_sec"] == 2.0
    assert data["check_uidvalidity"] is True


@pytest.mark.asyncio
async def test_put_creates_settings(client, admin_token):
    payload = {"max_email_age_days": 30, "processing_delay_sec": 5.0, "check_uidvalidity": False}
    resp = await client.put("/api/v1/settings/imap", json=payload, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_email_age_days"] == 30
    assert data["processing_delay_sec"] == 5.0
    assert data["check_uidvalidity"] is False


@pytest.mark.asyncio
async def test_put_updates_existing(client, admin_token):
    await client.put(
        "/api/v1/settings/imap",
        json={"max_email_age_days": 30, "processing_delay_sec": 5.0, "check_uidvalidity": False},
        headers=auth(admin_token),
    )
    resp = await client.put(
        "/api/v1/settings/imap",
        json={"max_email_age_days": 14, "processing_delay_sec": 1.0, "check_uidvalidity": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_email_age_days"] == 14
    assert data["processing_delay_sec"] == 1.0
    assert data["check_uidvalidity"] is True


@pytest.mark.asyncio
async def test_get_after_put(client, admin_token):
    await client.put(
        "/api/v1/settings/imap",
        json={"max_email_age_days": 60, "processing_delay_sec": 3.0, "check_uidvalidity": True},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/settings/imap", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["max_email_age_days"] == 60


@pytest.mark.asyncio
async def test_non_admin_denied(client, user_token):
    resp = await client.get("/api/v1/settings/imap", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_denied(client):
    resp = await client.get("/api/v1/settings/imap")
    assert resp.status_code in (401, 403)
