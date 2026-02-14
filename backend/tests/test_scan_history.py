import pytest
from unittest.mock import patch, AsyncMock

from app.core.encryption import encrypt_value
from app.models.email_account import EmailAccount
from app.models.email_scan import EmailScan


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "pass123"}
    )
    return resp.json()["access_token"]


@pytest.fixture
async def admin_user(client, admin_token):
    resp = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    return resp.json()


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "user1", "password": "pass"}
    )
    return login.json()["access_token"]


@pytest.fixture
async def account_with_scans(db_session, admin_user):
    account = EmailAccount(
        user_id=admin_user["id"],
        name="Test Account",
        imap_host="imap.example.com",
        imap_port=993,
        imap_user="test@example.com",
        imap_password_encrypted=encrypt_value("password123"),
        use_ssl=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    scans = []
    for i in range(5):
        scan = EmailScan(
            account_id=account.id,
            folder_path="INBOX",
            email_uid=100 + i,
            message_id=f"<msg-{i}@example.com>",
            subject=f"Order confirmation #{i}",
            sender=f"shop{i}@example.com",
            is_relevant=i % 2 == 0,  # 0,2,4 are relevant (3 total)
        )
        db_session.add(scan)
        scans.append(scan)

    await db_session.commit()
    for s in scans:
        await db_session.refresh(s)

    return {"account": account, "scans": scans}


# --- List Scan History ---


@pytest.mark.asyncio
async def test_list_scan_history(client, admin_token, account_with_scans):
    resp = await client.get("/api/v1/scan-history", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["page"] == 1
    assert data["per_page"] == 50
    # Verify account_name is populated
    for item in data["items"]:
        assert item["account_name"] == "Test Account"


@pytest.mark.asyncio
async def test_list_scan_history_filter_relevant(
    client, admin_token, account_with_scans
):
    resp = await client.get(
        "/api/v1/scan-history?is_relevant=true", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert all(item["is_relevant"] for item in data["items"])


@pytest.mark.asyncio
async def test_list_scan_history_pagination(client, admin_token, account_with_scans):
    resp = await client.get(
        "/api/v1/scan-history?page=1&per_page=2", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2

    # Get page 2
    resp2 = await client.get(
        "/api/v1/scan-history?page=2&per_page=2", headers=auth(admin_token)
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 2

    # Get page 3 (last page, 1 item)
    resp3 = await client.get(
        "/api/v1/scan-history?page=3&per_page=2", headers=auth(admin_token)
    )
    data3 = resp3.json()
    assert len(data3["items"]) == 1


# --- Get Scan Detail ---


@pytest.mark.asyncio
async def test_get_scan_detail(client, admin_token, account_with_scans):
    scan = account_with_scans["scans"][0]
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == scan.id
    assert data["subject"] == scan.subject
    assert data["sender"] == scan.sender
    assert data["account_name"] == "Test Account"


@pytest.mark.asyncio
async def test_get_scan_not_found(client, admin_token):
    resp = await client.get("/api/v1/scan-history/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Delete Scan ---


@pytest.mark.asyncio
async def test_delete_scan(client, admin_token, account_with_scans):
    scan = account_with_scans["scans"][0]
    resp = await client.delete(
        f"/api/v1/scan-history/{scan.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_scan_not_found(client, admin_token):
    resp = await client.delete("/api/v1/scan-history/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Queue Rescan ---


@pytest.mark.asyncio
async def test_queue_rescan(client, admin_token, account_with_scans):
    scan = account_with_scans["scans"][0]
    assert not scan.rescan_queued

    resp = await client.post(
        f"/api/v1/scan-history/{scan.id}/rescan", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rescan_queued"] is True
    assert data["id"] == scan.id


@pytest.mark.asyncio
async def test_queue_rescan_not_found(client, admin_token):
    resp = await client.post(
        "/api/v1/scan-history/9999/rescan", headers=auth(admin_token)
    )
    assert resp.status_code == 404


# --- User Isolation ---


@pytest.mark.asyncio
async def test_user_cannot_see_other_users_scans(
    client, db_session, admin_token, user_token, account_with_scans
):
    scan = account_with_scans["scans"][0]

    # User1 should see empty list
    resp = await client.get("/api/v1/scan-history", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

    # User1 cannot access admin's scan by ID
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}", headers=auth(user_token)
    )
    assert resp.status_code == 404

    # User1 cannot delete admin's scan
    resp = await client.delete(
        f"/api/v1/scan-history/{scan.id}", headers=auth(user_token)
    )
    assert resp.status_code == 404

    # User1 cannot rescan admin's scan
    resp = await client.post(
        f"/api/v1/scan-history/{scan.id}/rescan", headers=auth(user_token)
    )
    assert resp.status_code == 404


# --- Fetch Email Content ---


@pytest.mark.asyncio
@patch("app.api.scan_history.fetch_email_by_uid")
async def test_fetch_email_content(mock_fetch, client, admin_token, account_with_scans):
    mock_fetch.return_value = {
        "subject": "Your order has shipped",
        "sender": "orders@shop.com",
        "date": "Mon, 10 Feb 2025 12:00:00 +0000",
        "body_text": "Your package is on its way!",
    }

    scan = account_with_scans["scans"][0]
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}/email", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == "Your order has shipped"
    assert data["sender"] == "orders@shop.com"
    assert data["body_text"] == "Your package is on its way!"

    # Verify the mock was called with the right arguments
    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args
    assert call_args[0][1] == "INBOX"
    assert call_args[0][2] == scan.email_uid


@pytest.mark.asyncio
@patch("app.api.scan_history.fetch_email_by_uid")
async def test_fetch_email_not_on_server(
    mock_fetch, client, admin_token, account_with_scans
):
    mock_fetch.return_value = None

    scan = account_with_scans["scans"][0]
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}/email", headers=auth(admin_token)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Email not found on server"


@pytest.mark.asyncio
@patch("app.api.scan_history.fetch_email_by_uid")
async def test_fetch_email_user_isolation(
    mock_fetch, client, user_token, account_with_scans
):
    """User1 should not be able to fetch email content for admin's scan."""
    mock_fetch.return_value = {
        "subject": "Test",
        "sender": "test@test.com",
        "date": "",
        "body_text": "body",
    }

    scan = account_with_scans["scans"][0]
    resp = await client.get(
        f"/api/v1/scan-history/{scan.id}/email", headers=auth(user_token)
    )
    assert resp.status_code == 404
    # fetch_email_by_uid should NOT have been called
    mock_fetch.assert_not_called()


# --- Unauthenticated ---


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    resp = await client.get("/api/v1/scan-history")
    assert resp.status_code in (401, 403)
