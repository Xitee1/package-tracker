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
async def test_get_returns_empty_when_not_configured(client, admin_token):
    resp = await client.get("/api/v1/modules/providers/email-global/config", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_patch_creates_config(client, admin_token):
    payload = {
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "imap_user": "global@example.com",
        "imap_password": "secret",
        "use_ssl": True,
        "watched_folder_path": "INBOX",
    }
    resp = await client.patch("/api/v1/modules/providers/email-global/config", json=payload, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["imap_host"] == "imap.example.com"
    assert data["imap_user"] == "global@example.com"
    assert "imap_password" not in data  # password should not be returned


@pytest.mark.asyncio
async def test_patch_updates_existing(client, admin_token):
    payload = {
        "imap_host": "imap.example.com",
        "imap_user": "global@example.com",
        "imap_password": "secret",
    }
    await client.patch("/api/v1/modules/providers/email-global/config", json=payload, headers=auth(admin_token))
    # Update without password
    payload2 = {
        "imap_host": "imap2.example.com",
        "imap_user": "global@example.com",
    }
    resp = await client.patch("/api/v1/modules/providers/email-global/config", json=payload2, headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["imap_host"] == "imap2.example.com"


@pytest.mark.asyncio
async def test_non_admin_denied(client, user_token):
    resp = await client.get("/api/v1/modules/providers/email-global/config", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_info_endpoint_as_user(client, admin_token, user_token):
    # Before config: not configured
    resp = await client.get("/api/v1/providers/email-global/info", headers=auth(user_token))
    assert resp.status_code == 200
    assert resp.json()["configured"] is False

    # Enable email-global module
    await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(admin_token),
    )

    # Create config
    await client.patch(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "imap.example.com",
            "imap_user": "global@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )

    # After config + module enabled: configured with email
    resp = await client.get("/api/v1/providers/email-global/info", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["email_address"] == "global@example.com"


@pytest.mark.asyncio
async def test_info_returns_unconfigured_when_module_disabled(client, admin_token, user_token):
    # Create config (module not enabled by default)
    await client.patch(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "imap.example.com",
            "imap_user": "global@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )
    # Module not enabled — info should show not configured
    resp = await client.get("/api/v1/providers/email-global/info", headers=auth(user_token))
    assert resp.status_code == 200
    assert resp.json()["configured"] is False
