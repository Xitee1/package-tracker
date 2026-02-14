from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_folders_returns_404_when_not_configured(client, admin_token):
    resp = await client.get("/api/v1/modules/providers/email-global/folders", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_folders_returns_list(client, admin_token):
    # Create config first
    await client.put(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "imap.example.com",
            "imap_user": "global@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )

    mock_mail = MagicMock()
    mock_mail.login.return_value = ("OK", [])
    mock_mail.capability.return_value = ("OK", [b"IMAP4rev1 IDLE"])
    mock_mail.list.return_value = ("OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Sent"'])
    mock_mail.logout.return_value = ("BYE", [])

    with patch("app.modules.providers.email_global.router.imaplib") as mock_imaplib:
        mock_imaplib.IMAP4_SSL.return_value = mock_mail
        resp = await client.get("/api/v1/modules/providers/email-global/folders", headers=auth(admin_token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["folders"] == ["INBOX", "Sent"]
    assert data["idle_supported"] is True


@pytest.mark.asyncio
async def test_folders_connection_failure(client, admin_token):
    await client.put(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "bad.host",
            "imap_user": "user@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )

    with patch("app.modules.providers.email_global.router.imaplib") as mock_imaplib:
        mock_imaplib.IMAP4_SSL.side_effect = Exception("Connection refused")
        resp = await client.get("/api/v1/modules/providers/email-global/folders", headers=auth(admin_token))

    assert resp.status_code == 400
    assert "Failed to connect" in resp.json()["detail"]
