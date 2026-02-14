import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def create_account_and_folder(client, token):
    account = await client.post("/api/v1/accounts", json={
        "name": "Test", "imap_host": "imap.test.com", "imap_port": 993,
        "imap_user": "user", "imap_password": "pass", "use_ssl": True, "polling_interval_sec": 120,
    }, headers=auth(token))
    account_id = account.json()["id"]
    folder = await client.post(f"/api/v1/accounts/{account_id}/folders/watched",
        json={"folder_path": "INBOX"}, headers=auth(token))
    return account_id, folder.json()["id"]


@pytest.mark.asyncio
async def test_patch_watched_folder_overrides(client, admin_token):
    account_id, folder_id = await create_account_and_folder(client, admin_token)
    resp = await client.patch(f"/api/v1/accounts/{account_id}/folders/watched/{folder_id}",
        json={"max_email_age_days": 30}, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_email_age_days"] == 30


@pytest.mark.asyncio
async def test_patch_partial_update(client, admin_token):
    account_id, folder_id = await create_account_and_folder(client, admin_token)
    resp = await client.patch(f"/api/v1/accounts/{account_id}/folders/watched/{folder_id}",
        json={"max_email_age_days": 14}, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_email_age_days"] == 14


@pytest.mark.asyncio
async def test_watched_folder_response_includes_overrides(client, admin_token):
    account_id, folder_id = await create_account_and_folder(client, admin_token)
    resp = await client.get(f"/api/v1/accounts/{account_id}/folders/watched", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["max_email_age_days"] is None
