from unittest.mock import patch, AsyncMock
import pytest

from app.modules._shared.email.imap_utils import ImapFoldersResult


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
    await client.patch(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "imap.example.com",
            "imap_user": "global@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )

    mock_result = ImapFoldersResult(folders=["INBOX", "Sent"], idle_supported=True)

    with patch(
        "app.modules.providers.email_global.router.list_imap_folders",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.get("/api/v1/modules/providers/email-global/folders", headers=auth(admin_token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["folders"] == ["INBOX", "Sent"]
    assert data["idle_supported"] is True


@pytest.mark.asyncio
async def test_folders_connection_failure(client, admin_token):
    await client.patch(
        "/api/v1/modules/providers/email-global/config",
        json={
            "imap_host": "bad.host",
            "imap_user": "user@example.com",
            "imap_password": "secret",
        },
        headers=auth(admin_token),
    )

    with patch(
        "app.modules.providers.email_global.router.list_imap_folders",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        resp = await client.get("/api/v1/modules/providers/email-global/folders", headers=auth(admin_token))

    assert resp.status_code == 400
    assert "Failed to connect" in resp.json()["detail"]
