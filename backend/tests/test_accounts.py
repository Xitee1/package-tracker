from unittest.mock import patch

import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


ACCOUNT_DATA = {
    "name": "My Gmail",
    "imap_host": "imap.gmail.com",
    "imap_port": 993,
    "imap_user": "test@gmail.com",
    "imap_password": "secret123",
    "use_ssl": True,
    "polling_interval_sec": 120,
}


@pytest.mark.asyncio
async def test_create_account(client, admin_token):
    resp = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Gmail"
    assert data["imap_host"] == "imap.gmail.com"
    assert data["imap_user"] == "test@gmail.com"
    assert data["is_active"] is True
    assert "imap_password" not in data


@pytest.mark.asyncio
async def test_list_accounts(client, admin_token):
    await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    resp = await client.get("/api/v1/providers/email-user/accounts", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "My Gmail"


@pytest.mark.asyncio
async def test_list_accounts_empty(client, admin_token):
    resp = await client.get("/api/v1/providers/email-user/accounts", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_account(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/providers/email-user/accounts/{account_id}",
        json={"name": "Updated Name", "polling_interval_sec": 300},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["polling_interval_sec"] == 300
    assert resp.json()["imap_host"] == "imap.gmail.com"


@pytest.mark.asyncio
async def test_update_account_not_found(client, admin_token):
    resp = await client.patch(
        "/api/v1/providers/email-user/accounts/9999",
        json={"name": "Updated"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_account(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/providers/email-user/accounts/{account_id}", headers=auth(admin_token))
    assert resp.status_code == 204
    # Verify it's gone
    resp = await client.get("/api/v1/providers/email-user/accounts", headers=auth(admin_token))
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_account_not_found(client, admin_token):
    resp = await client.delete("/api/v1/providers/email-user/accounts/9999", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_account_isolation_between_users(client, admin_token):
    """Accounts should only be visible to their owner."""
    # Admin creates an account
    await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    # Create a regular user
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    user_token = login.json()["access_token"]
    # Regular user should see no accounts
    resp = await client.get("/api/v1/providers/email-user/accounts", headers=auth(user_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    resp = await client.get("/api/v1/providers/email-user/accounts")
    assert resp.status_code in (401, 403)


# --- Watched Folders ---

@pytest.mark.asyncio
async def test_add_watched_folder(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    assert resp.json()["folder_path"] == "INBOX"
    assert resp.json()["last_seen_uid"] == 0


@pytest.mark.asyncio
async def test_list_watched_folders(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"},
        headers=auth(admin_token),
    )
    await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "Shipping"},
        headers=auth(admin_token),
    )
    resp = await client.get(f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    folder_paths = [f["folder_path"] for f in resp.json()]
    assert "INBOX" in folder_paths
    assert "Shipping" in folder_paths


@pytest.mark.asyncio
async def test_remove_watched_folder(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    folder_resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"},
        headers=auth(admin_token),
    )
    folder_id = folder_resp.json()["id"]
    resp = await client.delete(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched/{folder_id}",
        headers=auth(admin_token),
    )
    assert resp.status_code == 204
    # Verify it's gone
    resp = await client.get(f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched", headers=auth(admin_token))
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_remove_watched_folder_not_found(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.delete(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched/9999",
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_watched_folder_on_nonexistent_account(client, admin_token):
    resp = await client.get("/api/v1/providers/email-user/accounts/9999/folders/watched", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Scan Watched Folder ---

@pytest.mark.asyncio
async def test_scan_watched_folder(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    folder_resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"},
        headers=auth(admin_token),
    )
    folder_id = folder_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched/{folder_id}/scan",
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scan_triggered"


@pytest.mark.asyncio
async def test_scan_folder_not_found(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched/9999/scan",
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scan_folder_on_nonexistent_account(client, admin_token):
    resp = await client.post(
        "/api/v1/providers/email-user/accounts/9999/folders/watched/1/scan",
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scan_folder_already_scanning(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    folder_resp = await client.post(
        f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"},
        headers=auth(admin_token),
    )
    folder_id = folder_resp.json()["id"]
    with patch("app.modules.providers.email_user.user_router.is_folder_scanning", return_value=True):
        resp = await client.post(
            f"/api/v1/providers/email-user/accounts/{account_id}/folders/watched/{folder_id}/scan",
            headers=auth(admin_token),
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_scan_unauthenticated(client):
    resp = await client.post("/api/v1/providers/email-user/accounts/1/folders/watched/1/scan")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_account_has_idle_fields(client, admin_token):
    resp = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["use_polling"] is False
    assert data["idle_supported"] is None


@pytest.mark.asyncio
async def test_update_use_polling(client, admin_token):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/providers/email-user/accounts/{account_id}",
        json={"use_polling": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["use_polling"] is True


@pytest.mark.asyncio
async def test_reject_disable_polling_when_idle_unsupported(client, admin_token, db_session):
    create = await client.post("/api/v1/providers/email-user/accounts", json=ACCOUNT_DATA, headers=auth(admin_token))
    account_id = create.json()["id"]
    from app.modules.providers.email_user.models import EmailAccount
    account = await db_session.get(EmailAccount, account_id)
    account.idle_supported = False
    account.use_polling = True
    await db_session.commit()
    resp = await client.patch(
        f"/api/v1/providers/email-user/accounts/{account_id}",
        json={"use_polling": False},
        headers=auth(admin_token),
    )
    assert resp.status_code == 400
    assert "IMAP IDLE" in resp.json()["detail"]
